"""
Tests para pii_guard.py — 9 casos del plan original.
Ejecutar con: pytest tests/test_pii_guard.py -v
"""
import sys
import os
import pytest
from unittest.mock import patch

# Añadir sync_worker al PYTHONPATH para importar pii_guard
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sync_worker')))
from pii_guard import pseudonymize_text


# ── Test 1: detección y eliminación de PII básica ──────────────────────────
def test_1_pii_detectado_y_eliminado():
    """Caso base: nombre, NIF/NIE, email, ubicación desaparecen del output."""
    text = "Mi nombre es Juan Pérez, mi NIF es 12345678A y mi correo es juan@example.com. Vivo en Madrid."
    anon, mappings = pseudonymize_text(text)

    # Los valores originales NO deben aparecer en el texto anonimizado
    assert "Juan Pérez" not in anon, "Nombre propio sigue en el texto"
    assert "12345678A" not in anon, "NIF sigue en el texto"
    assert "juan@example.com" not in anon, "Email sigue en el texto"
    assert "Madrid" not in anon, "Ubicación sigue en el texto"

    # Los tokens de pseudonimización SÍ deben aparecer
    assert "[PERSON" in anon
    assert "[ES_NIF_NIE" in anon
    assert "[EMAIL_ADDRESS" in anon
    assert "[LOCATION" in anon

    # Los mappings deben preservar los valores originales
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


# ── Test 4: estabilidad de tokens (misma entidad → mismo token) ───────────
def test_4_estabilidad_de_tokens():
    """La misma entidad que aparece dos veces genera tokens distintos
    (PERSON_1 y PERSON_2) pero ambos tienen el mismo raw_value."""
    text = "Juan Pérez habló con Juan Pérez sobre el examen."
    anon, mappings = pseudonymize_text(text)

    person_mappings = [m for m in mappings if m["entity_type"] == "PERSON"]
    # Debe haber al menos una detección de persona
    assert len(person_mappings) >= 1, "No se detectó ninguna persona"
    # Todos los tokens de persona deben ser distintos (numeración única)
    tokens = [m["token"] for m in person_mappings]
    assert len(tokens) == len(set(tokens)), f"Tokens duplicados: {tokens}"
    # El valor original debe estar en cada mapping
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
    """Si el motor NLP lanza excepción, pseudonymize_text la propaga
    (no degrada silenciosamente a texto en claro)."""
    with patch("pii_guard.get_analyzer") as mock_analyzer:
        mock_analyzer.return_value.analyze.side_effect = RuntimeError("NLP crash")
        with pytest.raises(RuntimeError):
            pseudonymize_text("Mi nombre es Ana García, DNI 11111111H.")


# ── Test 7: el payload final no contiene el valor original (substring) ─────
def test_7_payload_no_contiene_valor_original():
    """Verificación explícita de substring: el texto anonimizado no
    contiene ningún raw_value de los mappings devueltos."""
    text = "Llámame al correo ana.garcia@ucm.es o busca mi NIE X1234567L."
    anon, mappings = pseudonymize_text(text)

    for m in mappings:
        assert m["raw_value"] not in anon, (
            f"raw_value '{m['raw_value']}' sigue presente en el texto anonimizado: {anon!r}"
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


# ── Test 9: doble barrera — texto ya tokenizado pasa sin alarma ────────────
def test_9_texto_ya_tokenizado_pasa_doble_barrera():
    """Si el texto ya está tokenizado (contiene [PERSON_1] etc.), la segunda
    pasada de pseudonymize_text no debe detectar PII residual."""
    already_anonymized = (
        "El alumno [PERSON_1] indicó que su correo es [EMAIL_ADDRESS_1] "
        "y su NIF es [ES_NIF_NIE_1]. Vive en [LOCATION_1]."
    )
    _, residual_mappings = pseudonymize_text(already_anonymized)
    assert residual_mappings == [], (
        f"La doble barrera disparó un falso positivo sobre texto ya tokenizado: "
        f"{residual_mappings}"
    )
