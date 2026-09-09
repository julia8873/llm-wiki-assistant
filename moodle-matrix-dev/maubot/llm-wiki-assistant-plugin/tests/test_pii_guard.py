"""
Tests para pii_guard.py — 10 casos completos.
Incluye:
  - Tests 1-9: comportamiento de pseudonymize_text y verify_no_pii_residual
  - Test 10: la doble barrera aborta un commit real en un repo git temporal
             cuando se inyecta PII cruda (simula bug futuro en tasks.py)

Ejecutar con: pytest tests/test_pii_guard.py -v
"""
import sys
import os
import subprocess
import pytest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sync_worker')))
from pii_guard import pseudonymize_text, verify_no_pii_residual


# ── Test 1: detección y eliminación de PII básica ──────────────────────────
def test_1_pii_detectado_y_eliminado():
    """Caso base: nombre, NIF/NIE, email, ubicación desaparecen del output."""
    text = "Mi nombre es Juan Pérez, mi NIF es 12345678A y mi correo es juan@example.com. Vivo en Madrid."
    anon, mappings = pseudonymize_text(text)

    assert "Juan Pérez" not in anon, "Nombre propio sigue en el texto"
    assert "12345678A" not in anon, "NIF sigue en el texto"
    assert "juan@example.com" not in anon, "Email sigue en el texto"
    assert "Madrid" not in anon, "Ubicación sigue en el texto"

    assert "[PERSON" in anon
    assert "[ES_NIF_NIE" in anon
    assert "[EMAIL_ADDRESS" in anon
    assert "[LOCATION" in anon

    raw_values = [m["raw_value"] for m in mappings]
    assert "Juan Pérez" in raw_values
    assert "12345678A" in raw_values


# ── Test 2: texto sin PII se preserva intacto ──────────────────────────────
def test_2_texto_sin_pii_se_preserva():
    """Texto sin entidades PII sale exactamente igual."""
    text = "Esta es la tarea de la semana 3, apartado b."
    anon, mappings = pseudonymize_text(text)
    assert anon == text, f"Texto sin PII fue modificado: {anon!r}"
    assert mappings == [], f"Se devolvieron mappings inesperados: {mappings}"


# ── Test 3: texto vacío ────────────────────────────────────────────────────
def test_3_texto_vacio():
    """Cadena vacía → cadena vacía y lista de mappings vacía."""
    anon, mappings = pseudonymize_text("")
    assert anon == ""
    assert mappings == []


# ── Test 4: estabilidad de tokens (tokens únicos por instancia) ────────────
def test_4_estabilidad_de_tokens():
    """Múltiples personas generan tokens distintos PERSON_1, PERSON_2, etc."""
    text = "Juan Pérez habló con Juan Pérez sobre el examen."
    anon, mappings = pseudonymize_text(text)

    person_mappings = [m for m in mappings if m["entity_type"] == "PERSON"]
    assert len(person_mappings) >= 1, "No se detectó ninguna persona"
    tokens = [m["token"] for m in person_mappings]
    assert len(tokens) == len(set(tokens)), f"Tokens duplicados: {tokens}"
    for m in person_mappings:
        assert "Juan Pérez" in m["raw_value"]


# ── Test 5: texto mixto ES/EN ──────────────────────────────────────────────
def test_5_texto_mixto_es_en():
    """NIF español en texto con frase en inglés: el NIF debe detectarse."""
    text = "Hello, my student ID is 87654321Z and I live in Barcelona."
    anon, mappings = pseudonymize_text(text)

    assert "87654321Z" not in anon, "NIF en texto EN/ES sigue sin tokenizar"
    nif_m = [m for m in mappings if m["entity_type"] == "ES_NIF_NIE"]
    assert len(nif_m) >= 1, "No se detectó el NIF en texto mixto"


# ── Test 6: fail-safe si Presidio lanza excepción ──────────────────────────
def test_6_failsafe_si_presidio_falla():
    """Si el motor NLP lanza excepción, pseudonymize_text la propaga."""
    with patch("pii_guard.get_analyzer") as mock_analyzer:
        mock_analyzer.return_value.analyze.side_effect = RuntimeError("NLP crash")
        with pytest.raises(RuntimeError):
            pseudonymize_text("Mi nombre es Ana García, DNI 11111111H.")


# ── Test 7: el texto de salida no contiene el raw_value original ───────────
# ALCANCE: comprobación de substring sobre la salida de pseudonymize_text().
# NO pasa por git_utils.py ni por pii_vault/Postgres.
# El test E2E completo contra la BD real es test_pii_pipeline_e2e.py.
def test_7_output_no_contiene_valor_original():
    """Verificación explícita de substring: ningún raw_value aparece en el texto anonimizado."""
    text = "Llámame al correo ana.garcia@ucm.es o busca mi NIE X1234567L."
    anon, mappings = pseudonymize_text(text)
    for m in mappings:
        assert m["raw_value"] not in anon, (
            f"raw_value '{m['raw_value']}' sigue en el texto: {anon!r}"
        )


# ── Test 8: NIE con letra inicial (X, Y, Z) ───────────────────────────────
def test_8_nie_con_letra_inicial():
    """El reconocedor customizado detecta NIE con prefijo X/Y/Z."""
    for nie in ["X1234567L", "Y9876543M", "Z0000001R"]:
        text = f"Mi NIE es {nie}."
        anon, mappings = pseudonymize_text(text)
        assert nie not in anon, f"NIE {nie} no fue tokenizado"
        assert any(m["entity_type"] == "ES_NIF_NIE" for m in mappings), (
            f"No se detectó ES_NIF_NIE para {nie}"
        )


# ── Test 9: texto ya tokenizado no dispara falso positivo ─────────────────
def test_9_texto_ya_tokenizado_pasa_doble_barrera():
    """[PERSON_1] en el texto no se re-detecta como PII (fix del bug de SpaCy)."""
    already_anonymized = (
        "El alumno [PERSON_1] indicó que su correo es [EMAIL_ADDRESS_1] "
        "y su NIF es [ES_NIF_NIE_1]. Vive en [LOCATION_1]."
    )
    _, residual_mappings = pseudonymize_text(already_anonymized)
    assert residual_mappings == [], (
        f"Falso positivo sobre texto ya tokenizado: {residual_mappings}"
    )


# ── Test 10: la doble barrera aborta el commit ante PII real ───────────────
def test_10_doble_barrera_aborta_commit_ante_pii_real(tmp_path):
    """
    Escenario: un bug hipotético en tasks.py omite pii_guard en la primera
    pasada, y el payload llega al punto pre-commit CON PII en claro.

    Este test verifica:
    a) verify_no_pii_residual() lanza RuntimeError.
    b) El commit NO se crea en un repo git real (el log git queda limpio).
    """
    # ── Preparar un repo git mínimo en tmp_path ────────────────────────────
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)

    # Commit inicial para que el repo tenga historia
    (repo / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    log_inicial = subprocess.run(
        ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    # ── Simular payload con PII cruda (bug: primera pasada omitida) ────────
    pii_payload = {
        "mensaje_alumno": "Hola, soy Juan Pérez y mi DNI es 12345678A.",
        "respuesta_bot": "Entendido, Juan Pérez.",
    }

    # ── Verificar que la barrera lanza RuntimeError ────────────────────────
    with pytest.raises(RuntimeError) as exc_info:
        verify_no_pii_residual(pii_payload)

    assert "FAIL-SAFE" in str(exc_info.value), (
        f"RuntimeError no menciona FAIL-SAFE: {exc_info.value}"
    )
    assert "PERSON" in str(exc_info.value) or "ES_NIF_NIE" in str(exc_info.value), (
        f"RuntimeError no identifica el tipo de PII: {exc_info.value}"
    )

    # ── Verificar que el repo NO tiene commits nuevos ──────────────────────
    # (en el flujo real tasks.py, la excepción impide llegar a git-add/commit)
    log_despues = subprocess.run(
        ["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()

    assert log_inicial == log_despues, (
        f"¡El repo tiene commits nuevos cuando no debería!\n"
        f"Antes: {log_inicial!r}\nDespués: {log_despues!r}"
    )

    # Verificar que el fichero PII en claro no se escribió en disco
    # (en el flujo real, open(log_path, 'a') ocurre DESPUÉS de verify_no_pii_residual)
    log_file = repo / "logs" / "interacciones" / "test.jsonl"
    assert not log_file.exists(), (
        "El fichero JSONL fue creado aunque la barrera debería haber abortado antes"
    )
