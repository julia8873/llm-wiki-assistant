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

def pseudonymize_text(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Detects and pseudonymizes PII in the given text.
    Returns a tuple of (pseudonymized_text, mappings)
    Where mappings is a list of dicts: {"token": str, "raw_value": str, "entity_type": str}
    """
    if not text:
        return text, []

    analyzer = get_analyzer()
    anonymizer = get_anonymizer()

    # We use "es" as default because it's a Spanish course, but could use "en" if needed.
    # We will run both or just "es". Let's run "es".
    results = analyzer.analyze(text=text, entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "ES_NIF_NIE"], language="es")
    
    if not results:
        return text, []

    # Sort results by start index descending to replace from end to start without messing up indices
    results = sorted(results, key=lambda x: x.start, reverse=True)
    
    mappings = []
    # To generate unique tokens like [PERSON_1], [PERSON_2]
    counters = {}
    
    # We will build the anonymized text manually or let Presidio do it and then extract mappings.
    # It's easier to do it manually to map exactly which raw_value became which token.
    anonymized_text = text
    
    for res in results:
        entity_type = res.entity_type
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

    # Using MAPEO_API_URL or a new internal endpoint for metrics-api.
    # By default, MAPEO_API_URL points to bdc-trazabilidad metrics-api.
    metrics_api_url = os.getenv("MAPEO_API_URL")
    if not metrics_api_url:
        raise ValueError("MAPEO_API_URL not configured for PII guard.")
        
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
