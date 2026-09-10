import os
import requests
import logging
from typing import List, Dict, Tuple
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

logger = logging.getLogger(__name__)

# Initialize engines lazily to avoid heavy loading if not needed immediately
_analyzer = None
_anonymizer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "es", "model_name": "es_core_news_lg"},
                {"lang_code": "en", "model_name": "en_core_web_lg"}
            ]
        })
        nlp_engine = provider.create_engine()
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["es", "en"])
        
        # Add custom recognizer for ES_NIF_NIE
        nif_pattern = Pattern(
            name="nif_nie",
            regex=r"\b([XYZ]\d{7,8}[A-Z]|\d{8}[A-Z])\b",
            score=0.5
        )
        nif_recognizer = PatternRecognizer(
            supported_entity="ES_NIF_NIE",
            patterns=[nif_pattern],
            supported_language="es"
        )
        _analyzer.registry.add_recognizer(nif_recognizer)
    return _analyzer

def get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

import re as _re

# Patrón que reconoce cualquier token de pseudonimización ya existente, p.ej. [PERSON_1]
_TOKEN_RE = _re.compile(r'\[[A-Z_]+_\d+\]')
# Placeholder neutro que SpaCy no identifica como entidad PII
_TOKEN_PLACEHOLDER = "XXXXXXXX"

def pseudonymize_text(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Detects and pseudonymizes PII in the given text.
    Returns a tuple of (pseudonymized_text, mappings)
    Where mappings is a list of dicts: {"token": str, "raw_value": str, "entity_type": str}

    Tokens already present in the text (e.g. [PERSON_1] from a previous pass)
    are temporarily masked before analysis so SpaCy does not re-detect them
    as PII — preventing false positives in the double-barrier check.
    """
    if not text:
        return text, []

    analyzer = get_analyzer()

    # ── Pre-procesado: enmascarar tokens existentes ────────────────────────
    # Guardar las posiciones y valores originales de los tokens ya presentes
    existing_tokens = []
    masked_text = text
    offset = 0
    for m in _TOKEN_RE.finditer(text):
        start = m.start() + offset
        end = m.end() + offset
        original = m.group()
        # Sustituir por placeholder de la misma longitud para no desplazar índices
        placeholder = _TOKEN_PLACEHOLDER[:len(original)].ljust(len(original), 'X')
        masked_text = masked_text[:start] + placeholder + masked_text[end:]
        existing_tokens.append((start, start + len(placeholder), original))
        # offset no cambia porque reemplazamos exactamente la misma longitud
    # ──────────────────────────────────────────────────────────────────────

    results = analyzer.analyze(
        text=masked_text,
        entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "ES_NIF_NIE"],
        language="es"
    )

    # Filtrar cualquier detección que caiga dentro de las posiciones de tokens existentes
    token_ranges = [(s, e) for (s, e, _) in existing_tokens]
    def _overlaps_existing(res) -> bool:
        for (ts, te) in token_ranges:
            if res.start < te and res.end > ts:
                return True
        return False

    results = [r for r in results if not _overlaps_existing(r)]

    if not results:
        return text, []

    # Sort by start index descending to replace from end to start
    results = sorted(results, key=lambda x: x.start, reverse=True)

    mappings = []
    counters = {}
    anonymized_text = text  # Trabajar sobre el texto ORIGINAL (con tokens, no enmascarado)

    for res in results:
        entity_type = res.entity_type
        # Extraer el raw_value del texto original (no del enmascarado)
        raw_value = text[res.start:res.end]

        counters[entity_type] = counters.get(entity_type, 0) + 1
        token = f"[{entity_type}_{counters[entity_type]}]"

        mappings.append({
            "token": token,
            "raw_value": raw_value,
            "entity_type": entity_type
        })

        anonymized_text = anonymized_text[:res.start] + token + anonymized_text[res.end:]

    return anonymized_text, mappings

def send_pii_to_vault(student_matrix_id: str, interaction_id: str, mappings: List[Dict[str, str]]):
    """
    Sends the PII mappings to the secure vault in bdc-trazabilidad.
    Raises an exception if it fails (fail-safe).
    """
    if not mappings:
        return

    internal_token = os.getenv("INTERNAL_SERVICE_TOKEN")
    if not internal_token:
        raise ValueError("INTERNAL_SERVICE_TOKEN not configured for PII guard.")

    metrics_api_url = os.getenv("METRICS_API_URL", "http://bdc-trazabilidad-metrics-api-1:8000")
    if not metrics_api_url:
        raise ValueError("METRICS_API_URL not configured for PII guard.")
        
    endpoint = f"{metrics_api_url.rstrip('/')}/internal/pii/vault"
    
    payload = {
        "student_matrix_id": student_matrix_id,
        "interaction_id": interaction_id,
        "mappings": mappings
    }
    
    try:
        resp = requests.post(
            endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {internal_token}"},
            timeout=10
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send PII to vault: {e}")
        # We must fail the commit flow if we can't secure the PII
        raise RuntimeError("Fail-safe: Could not store PII securely, aborting sync.") from e


def verify_no_pii_residual(
    log_data: dict,
    fields: tuple = ("mensaje_alumno", "respuesta_bot")
) -> None:
    """
    DOBLE BARRERA — re-ejecutar Presidio sobre los campos de texto del payload
    final para confirmar que NO queda ninguna entidad PII sin tokenizar.

    Llamar ANTES de git-add/commit. Si se detecta cualquier entidad,
    se lanza RuntimeError y el commit nunca llega a crearse en local.

    Esta función es pura y testeable de forma aislada.
    """
    for field in fields:
        value = log_data.get(field)
        if not isinstance(value, str) or not value:
            continue
        _, residual = pseudonymize_text(value)
        if residual:
            leaked_types = [m["entity_type"] for m in residual]
            logger.error(
                f"FAIL-SAFE doble barrera: campo '{field}' contiene "
                f"entidades PII sin tokenizar: {leaked_types}. "
                f"Abortando antes de git-commit."
            )
            raise RuntimeError(
                f"FAIL-SAFE: PII detectado en campo '{field}' "
                f"({leaked_types}). Commit abortado."
            )
