import sys
import os
import pytest

# Añadir sync_worker al PYTHONPATH para importar pii_guard
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sync_worker')))
from pii_guard import pseudonymize_text

def test_pseudonymize_text():
    text = "Hola, mi nombre es Juan Pérez, mi NIF es 12345678A y mi correo es juan@example.com. Vivo en Madrid."
    anon, mappings = pseudonymize_text(text)
    
    assert "Juan Pérez" not in anon
    assert "12345678A" not in anon
    assert "juan@example.com" not in anon
    assert "Madrid" not in anon
    
    assert "[PERSON" in anon
    assert "[ES_NIF_NIE" in anon
    assert "[LOCATION" in anon
    assert "[EMAIL_ADDRESS" in anon
    
    # Comprobar mappings
    raw_values = [m["raw_value"] for m in mappings]
    assert "Juan Pérez" in raw_values
    assert "12345678A" in raw_values
    
def test_pseudonymize_text_empty():
    anon, mappings = pseudonymize_text("")
    assert anon == ""
    assert mappings == []
