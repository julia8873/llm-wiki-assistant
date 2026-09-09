import os
import requests
import pytest
import datetime

# Asegúrate de que los contenedores estén levantados antes de correr este test.
# metrics-api debería estar en el host en el 8000
METRICS_API_URL = os.getenv("MAPEO_API_URL", "http://host.docker.internal:8000")
INTERNAL_TOKEN = "dev_internal_token"

def test_pii_vault_and_reveal():
    # 1. Almacenar PII (simulando sync_worker)
    vault_url = f"{METRICS_API_URL}/internal/pii/vault"
    interaction_id = "test_interaction_e2e"
    payload = {
        "student_matrix_id": "@test_user:localhost",
        "interaction_id": interaction_id,
        "mappings": [
            {
                "token": "[PERSON_1]",
                "raw_value": "Juan Pérez E2E",
                "entity_type": "PERSON"
            }
        ]
    }
    
    headers = {"Authorization": f"Bearer {INTERNAL_TOKEN}"}
    response = requests.post(vault_url, json=payload, headers=headers)
    assert response.status_code == 201, f"Error al guardar en vault: {response.text}"
    
    # 2. Intentar revelar sin ser profesor (debería fallar o requerir auth)
    # Primero necesitamos generar un JWT válido de profesor.
    # Como esto es un test, podemos hacer login en metrics-api si existe un usuario de prueba,
    # o simplemente verificar que sin token falla.
    reveal_url = f"{METRICS_API_URL}/v1/metrics/pii/reveal"
    reveal_payload = {
        "token": "[PERSON_1]",
        "interaction_id": interaction_id
    }
    
    response_no_auth = requests.post(reveal_url, json=reveal_payload)
    assert response_no_auth.status_code in [401, 403], "Debería fallar sin autenticación"
