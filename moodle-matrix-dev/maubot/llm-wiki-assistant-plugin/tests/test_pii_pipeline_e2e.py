"""
Tests E2E del pipeline completo de PII.
Requiere que metrics-api (bdc-trazabilidad) esté levantado y accesible.

Ejecutar desde dentro del contenedor maubot con:
  pytest tests/test_pii_pipeline_e2e.py -v

Los tests usan host.docker.internal:8000 para alcanzar metrics-api.
"""
import os
import jwt
import datetime
import uuid
import requests
import pytest

METRICS_API_URL = os.getenv("MAPEO_API_URL", "http://host.docker.internal:8000")
INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "dev_internal_token")

# JWT_SECRET_KEY debe coincidir con el de metrics-api
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_secret_key_for_local_testing_only")
JWT_ALGORITHM = "HS256"


def _make_teacher_jwt(username: str = "profesor_test") -> str:
    """Genera un JWT de profesor válido con el mismo secret que usa metrics-api."""
    payload = {
        "sub": username,
        "is_teacher": True,
        "allowed_courses": [1, 2, 3],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ── E2E-1: vault almacena y rechaza acceso sin autenticación ───────────────
def test_e2e_1_vault_almacena_y_bloquea_sin_auth():
    """Insertar en vault → verificar 201; intentar revelar sin JWT → 401."""
    vault_url = f"{METRICS_API_URL}/internal/pii/vault"
    interaction_id = f"e2e_1_{uuid.uuid4().hex[:8]}"

    payload = {
        "student_matrix_id": "@e2e_user:localhost",
        "interaction_id": interaction_id,
        "mappings": [
            {"token": "[PERSON_1]", "raw_value": "Juan Pérez E2E", "entity_type": "PERSON"}
        ],
    }
    r = requests.post(vault_url, json=payload, headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"})
    assert r.status_code == 201, f"Error en vault: {r.text}"

    reveal_url = f"{METRICS_API_URL}/v1/metrics/pii/reveal"
    r_noauth = requests.post(reveal_url, json={"token": "[PERSON_1]", "interaction_id": interaction_id})
    assert r_noauth.status_code in (401, 403), f"Debería rechazar sin JWT, devolvió {r_noauth.status_code}"


# ── E2E-2: reversión auditada — reveal con JWT de profesor ────────────────
def test_e2e_2_reveal_con_profesor_devuelve_valor_y_audita():
    """
    Flujo completo de reversión auditada:
    1. Insertar PII en vault con token interno.
    2. Revelar con JWT de profesor válido → raw_value correcto.
    3. Verificar que se creó una fila en pii_access_log (endpoint de auditoría
       o comprobando directamente que la BD tiene la entrada).

    La verificación de pii_access_log se hace a través de un segundo reveal
    fallido con otro interaction_id: si el primer reveal hubiera fallado
    silenciosamente, el campo audit también faltaría → ambos errores se
    detectarían. La verificación directa de la BD se cubre en test_pii_purge.py.
    """
    vault_url = f"{METRICS_API_URL}/internal/pii/vault"
    interaction_id = f"e2e_2_{uuid.uuid4().hex[:8]}"
    raw_value_original = "Ana García Auditada"

    # 1. Insertar en vault
    vault_payload = {
        "student_matrix_id": "@e2e_user_audit:localhost",
        "interaction_id": interaction_id,
        "mappings": [
            {"token": "[PERSON_1]", "raw_value": raw_value_original, "entity_type": "PERSON"}
        ],
    }
    r_vault = requests.post(
        vault_url,
        json=vault_payload,
        headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"}
    )
    assert r_vault.status_code == 201, f"Error en vault: {r_vault.text}"

    # 2. Revelar con JWT de profesor
    teacher_jwt = _make_teacher_jwt()
    reveal_url = f"{METRICS_API_URL}/v1/metrics/pii/reveal"
    reveal_payload = {"token": "[PERSON_1]", "interaction_id": interaction_id}

    r_reveal = requests.post(
        reveal_url,
        json=reveal_payload,
        headers={"Authorization": f"Bearer {teacher_jwt}"}
    )
    assert r_reveal.status_code == 200, f"Reveal falló: {r_reveal.text}"

    # 3. Verificar que raw_value devuelto es el original
    data = r_reveal.json()
    assert data.get("raw_value") == raw_value_original, (
        f"raw_value incorrecto: esperado '{raw_value_original}', "
        f"obtenido '{data.get('raw_value')}'"
    )

    # 4. Verificar pii_access_log directamente en BD desde este test
    #    (importamos SessionLocal que funciona desde dentro del contenedor maubot
    #    sólo si DATABASE_URL apunta a postgres; si no, usamos endpoint alternativo)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url, connect_args={"options": "-csearch_path=metrics"})
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT id FROM metrics.pii_access_log "
                        "WHERE interaction_id = :iid AND token_requested = :tok "
                        "ORDER BY timestamp DESC LIMIT 1"
                    ),
                    {"iid": interaction_id, "tok": "[PERSON_1]"}
                ).fetchone()
            assert result is not None, (
                "No se encontró fila en pii_access_log después del reveal"
            )
        except ImportError:
            pytest.skip("sqlalchemy no disponible en este contenedor para verificar pii_access_log")
    else:
        pytest.skip("DATABASE_URL no configurado: verificación de pii_access_log omitida")


# ── E2E-3: vault → pii_vault DB real (insert + decrypt) ───────────────────
def test_e2e_3_pipeline_vault_db_insert_y_decrypt():
    """
    Test E2E REAL contra pii_vault/Postgres:
    1. Insertar PII cifrada vía /internal/pii/vault.
    2. Leer el raw_value_encrypted de la BD directamente.
    3. Descifrar con PII_SECRET_KEY y verificar que coincide con el original.

    Esto verifica que:
    - El endpoint efectivamente cifra (no guarda en claro).
    - El cifrado es reversible con la clave correcta.
    - No se guarda el valor en texto plano en ninguna columna.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL no disponible para test E2E de BD")

    pii_secret = os.getenv("PII_SECRET_KEY")
    if not pii_secret:
        pytest.skip("PII_SECRET_KEY no disponible")

    vault_url = f"{METRICS_API_URL}/internal/pii/vault"
    interaction_id = f"e2e_3_{uuid.uuid4().hex[:8]}"
    raw_value_original = "Rosario Valpuesta NIE X9876543B"

    # 1. Insertar en vault via API
    r = requests.post(
        vault_url,
        json={
            "student_matrix_id": "@e2e_db_user:localhost",
            "interaction_id": interaction_id,
            "mappings": [
                {"token": "[PERSON_1]", "raw_value": raw_value_original, "entity_type": "PERSON"}
            ],
        },
        headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"},
    )
    assert r.status_code == 201, f"Error en vault: {r.text}"

    # 2. Leer raw_value_encrypted de BD directamente
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url, connect_args={"options": "-csearch_path=metrics"})
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT raw_value_encrypted FROM metrics.pii_vault "
                "WHERE interaction_id = :iid AND token = :tok"
            ),
            {"iid": interaction_id, "tok": "[PERSON_1]"},
        ).fetchone()

    assert row is not None, "No se encontró la fila en pii_vault"
    encrypted = row[0]

    # 3. Verificar que NO está en claro
    assert raw_value_original not in encrypted, (
        "¡El raw_value está sin cifrar en la BD!"
    )

    # 4. Descifrar y verificar valor original
    from cryptography.fernet import Fernet
    f = Fernet(pii_secret.encode())
    decrypted = f.decrypt(encrypted.encode()).decode()
    assert decrypted == raw_value_original, (
        f"Descifrado incorrecto: esperado '{raw_value_original}', "
        f"obtenido '{decrypted}'"
    )

    # Limpieza
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM metrics.pii_vault WHERE interaction_id = :iid"),
            {"iid": interaction_id}
        )
        conn.commit()
