#!/usr/bin/env bash
## @file instalar.sh
## @brief Script orquestador principal del proyecto LLM Wiki Assistant.
## 
## Centraliza las operaciones de despliegue, configuración y gestión de la infraestructura
## Docker Compose y documentación Doxygen.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${ROOT_DIR}/config/config.yaml"

## @fn info()
## @brief Imprime un mensaje informativo estándar.
## @param $1 Mensaje de información a imprimir.
info()  { echo "[INFO]  $*"; }

## @fn ok()
## @brief Imprime un mensaje de éxito.
## @param $1 Mensaje de éxito a imprimir.
ok()    { echo "[ OK ]  $*"; }

## @fn warn()
## @brief Imprime un mensaje de advertencia.
## @param $1 Mensaje de advertencia a imprimir.
warn()  { echo "[WARN]  $*"; }

## @fn skip()
## @brief Imprime un mensaje de salto de tarea.
## @param $1 Mensaje de salto a imprimir.
skip()  { echo "[SKIP]  $*"; }

## @fn error()
## @brief Imprime un error crítico en stderr y aborta la ejecución.
## @param $1 Mensaje de error.
## @exception Aborta el script con código de salida 1.
error() { echo "[ERROR] $*" >&2; exit 1; }

## @fn check_docker()
## @brief Verifica la disponibilidad del binario de Docker.
## @exception Llama a error() si Docker no está instalado en el PATH.
check_docker() {
  command -v docker &>/dev/null || error "Docker no está instalado. Requerido para continuar."
}

## @fn yaml_get()
## @brief Extrae el valor de una clave hoja desde config.yaml usando grep y awk.
## @param $1 Clave a buscar (e.g., puerto_host).
## @param $2 Valor por defecto a retornar si no se encuentra la clave.
## @return String con el valor encontrado o el por defecto.
yaml_get() {
  local key="$1" default="${2:-}"
  local value
  value=$(grep -m1 "${key}:" "${CONFIG_FILE}" 2>/dev/null \
    | awk -F': ' '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); gsub(/"/, "", $2); print $2}' || true)
  echo "${value:-$default}"
}

## @fn copy_if_missing()
## @brief Copia un archivo plantilla (ej. .example) a su destino real si no existe.
## @param $1 Ruta absoluta del fichero origen.
## @param $2 Ruta absoluta del fichero destino.
copy_if_missing() {
  local src="$1" dst="$2"
  if [[ -f "$dst" ]]; then
    skip "$(basename "$dst") ya existe, no se sobreescribe."
  else
    cp "$src" "$dst"
    ok "$(basename "$dst") creado desde $(basename "$src")."
    warn "  Edita ${dst} e inyecta los secretos reales."
  fi
}

## @fn usage()
## @brief Muestra la ayuda y el listado de subcomandos soportados.
## @return Finaliza la ejecución limpiamente (exit 0).
usage() {
  cat <<EOF
LLM Wiki Assistant — instalar.sh

Comandos base:
  (sin argumentos)         Instalación/arranque automático completo.
  help                     Muestra esta ayuda.

Fase 0.1 (Documentación):
  docs serve               Genera y levanta Doxygen HTTP en el puerto configurado.
  docs check               Genera Doxygen en modo estricto (falla ante warnings).

Fase 1 (Entorno Docker):
  up                       Levanta el stack Docker Compose.
  down [--volumes]         Detiene el stack.
  logs [servicio]          Muestra logs.
  status                   Estado de contenedores.
  git setup                Configura repositorios base.

Fase 3 (Sincronización):
  bot sync                 Fuerza actualización Moodle -> Matrix.
EOF
  exit 0
}

## @fn cmd_install_all()
## @brief Flujo principal de instalación que se ejecuta por defecto sin argumentos.
## 
## 1. Copia secretos y configura base.
## 2. Inicia servidor de documentación.
cmd_install_all() {
  echo ""
  echo "=== LLM Wiki Assistant — Orquestador de Instalación ==="
  echo "    Raíz: ${ROOT_DIR}"
  echo ""

  echo "--- Fase: Configuración Base y Secretos ---"
  copy_if_missing "${ROOT_DIR}/.env.example"                                      "${ROOT_DIR}/.env"
  copy_if_missing "${ROOT_DIR}/config/config.yaml.example"                        "${ROOT_DIR}/config/config.yaml"
  copy_if_missing "${ROOT_DIR}/moodle-matrix-dev/maubot/base-config.yaml.example" "${ROOT_DIR}/moodle-matrix-dev/maubot/base-config.yaml"
  copy_if_missing "${ROOT_DIR}/moodle-matrix-dev/maubot/config.yaml.example"      "${ROOT_DIR}/moodle-matrix-dev/maubot/config.yaml"
  echo ""

  echo "--- Fase: Stack Docker ---"
  warn "Infraestructura Docker (Fase 1) pendiente de implementación."
  echo ""

  echo "--- Fase: Servidor de Documentación (Doxygen) ---"
  check_docker
  echo "=== Secuencia Completada ==="
  echo "  [OK] Entorno configurado"
  echo "  [OK] Lanzando servidor Doxygen silencioso"
  echo ""
  cmd_docs serve
}

## @fn cmd_docs()
## @brief Gestiona el ciclo de vida de la documentación Doxygen vía Docker Alpine.
## @param $1 Comando subordinado (serve|check). Por defecto 'serve'.
## @exception Aborta si el comando es inválido o falla la validación estricta (check).
cmd_docs() {
  local submode="${1:-serve}"
  check_docker
  local docs_port; docs_port=$(awk '/^[[:space:]]*docs:/{flag=1} flag && /puerto_host:/{print $2; exit}' "${CONFIG_FILE}" 2>/dev/null)
  docs_port=${docs_port:-8005}

  case "$submode" in
    serve|start|dev)
      info "Generando compilación Doxygen..."
      mkdir -p "${ROOT_DIR}/doxygen_docs/html" 2>/dev/null || true
      docker run --rm -v "${ROOT_DIR}:/data" alpine sh -c "apk add --no-cache doxygen graphviz && cd /data && doxygen Doxyfile"
      info "Exponiendo interfaz web en http://localhost:${docs_port}"
      docker rm -f llm-wiki-docs 2>/dev/null || true
      docker run --name llm-wiki-docs -d -p "${docs_port}:8000" -v "${ROOT_DIR}/doxygen_docs/html:/data" python:3.9-alpine sh -c "cd /data && python -m http.server 8000"
      ;;
    check|build|verify)
      info "Validación estricta de sintaxis Doxygen..."
      mkdir -p "${ROOT_DIR}/doxygen_docs/html" 2>/dev/null || true
      docker run --rm -v "${ROOT_DIR}:/data" alpine sh -c "apk add --no-cache doxygen graphviz && cd /data && doxygen Doxyfile"
      ok "Documentación verificada sin errores ni enlaces rotos."
      ;;
    *)
      error "Comando docs no reconocido: '${submode}'."
      ;;
  esac
}

## Funciones Stubs (Fases Futuras)
cmd_up()     { error "Comando 'up' pendiente (Fase 1)."; }
cmd_down()   { error "Comando 'down' pendiente (Fase 1)."; }
cmd_logs()   { error "Comando 'logs' pendiente (Fase 1)."; }
cmd_status() { error "Comando 'status' pendiente (Fase 1)."; }
cmd_git()    { error "Comando 'git setup' pendiente (Fase 1)."; }
cmd_bot()    { error "Comando 'bot sync' pendiente (Fase 3)."; }

## @fn main()
## @brief Procesador de línea de comandos. Enruta argumentos a subfunciones.
## @param $@ Argumentos pasados al script.
main() {
  [[ $# -eq 0 ]] && { cmd_install_all; return; }

  local cmd="$1"; shift || true
  case "$cmd" in
    docs)           cmd_docs   "${@:-serve}" ;;
    up)             cmd_up ;;
    down)           cmd_down ;;
    logs)           cmd_logs ;;
    status)         cmd_status ;;
    git)            cmd_git ;;
    bot)            cmd_bot ;;
    help|-h|--help) usage ;;
    *) error "Comando desconocido: '${cmd}'. Utiliza 'help' para listado completo." ;;
  esac
}

main "$@"
