#!/usr/bin/env bash
## @file test-services.sh
## @brief Test de integración para verificar conectividad de los servicios de Fase 1.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ ! -f "${ROOT_DIR}/moodle-matrix-dev/.env" ]]; then
  echo "[ERROR] No existe el fichero .env. Ejecuta ./instalar.sh primero."
  exit 1
fi

source "${ROOT_DIR}/moodle-matrix-dev/.env"

check_port() {
  local service="$1"
  local port="$2"
  
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}" | grep -qE "(200|301|302|303|400|401|403|404|502)"; then
    echo "[ OK ] $service responde en el puerto $port"
  else
    echo "[FAIL] $service NO responde en el puerto $port"
    exit 1
  fi
}

echo "=== Verificando conectividad HTTP de Servicios ==="
check_port "Moodle" "${MOODLE_PUERTO_HOST:-8000}"
check_port "Synapse" "${SYNAPSE_PUERTO_HOST:-8008}"
check_port "Element" "${ELEMENT_PUERTO_HOST:-8081}"

echo "[ OK ] Integración de Fase 1 verificada."
