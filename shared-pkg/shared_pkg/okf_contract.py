"""Contrato de formato OKF y eventos de sincronización.

Este módulo define las constantes exactas (mensajes de commit, rutas, etc.)
que definen el formato OKF en llm-wiki-assistant, sirviendo de contrato
formal para que metrics-worker pueda parsear el historial de Git sin hardcodear
estas cadenas.
"""

OKF_CONTRACT_VERSION = "1.0.0"

# Mensajes de commit generados automáticamente por el bot
COMMIT_MSG_INGEST = "Ingesta automatica de conceptos"
COMMIT_MSG_REVERT = "Reversion automatica de la ultima ingesta"
COMMIT_MSG_SYNC = "Sincronización automática completa de material oficial"
COMMIT_MSG_LOG = "Log interacción"

# Rutas estándar del formato OKF
PATH_LOG_INTERACCIONES = "logs/interacciones"
PATH_INTERACCIONES = "okf/interacciones"

# Mensaje para la extracción de metadatos de interacciones
COMMIT_MSG_INTERACCION = "Extracción automática de interacciones"
