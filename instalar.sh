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
  copy_if_missing "${ROOT_DIR}/moodle-matrix-dev/.env.example" "${ROOT_DIR}/moodle-matrix-dev/.env"
  cmd_up "$@"
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

### @fn generate_env()
## @brief Genera el fichero .env combinando config.yaml y .env.example
generate_env() {
  local env_file="${ROOT_DIR}/moodle-matrix-dev/.env"
  local example_file="${ROOT_DIR}/moodle-matrix-dev/.env.example"
  
  info "Generando/Actualizando ${env_file} a partir de config.yaml..."
  
  # Bloque dinámico
  echo "# === BLOQUE GENERADO AUTOMÁTICAMENTE DESDE config.yaml ===" > "${env_file}.tmp"
  awk -F': ' '
    /^  [a-zA-Z_]+:/ { section=toupper($1); gsub(/ |:/, "", section) }
    /^    [a-zA-Z_]+:/ { key=toupper($1); gsub(/ |:/, "", key); val=$2; gsub(/"/, "", val); print section"_"key"="val }
  ' "${CONFIG_FILE}" >> "${env_file}.tmp"
  
  echo "" >> "${env_file}.tmp"
  echo "# === SECRETOS Y VARIABLES MANUALES ===" >> "${env_file}.tmp"
  
  # Copiar secretos (preservando existentes si los hay)
  if [[ -f "$env_file" ]] && grep -q "=== SECRETOS Y VARIABLES MANUALES ===" "$env_file"; then
    sed -n '/=== SECRETOS Y VARIABLES MANUALES ===/,$p' "$env_file" | tail -n +2 >> "${env_file}.tmp"
  elif [[ -f "$env_file" ]]; then
    cat "$env_file" >> "${env_file}.tmp"
  else
    cat "$example_file" >> "${env_file}.tmp"
  fi
  
  # Generar MAPEO_API_TOKEN si está en modo default
  if grep -q "MAPEO_API_TOKEN=changeme" "${env_file}.tmp"; then
    local new_token=$(openssl rand -hex 16)
    sed -i "s/MAPEO_API_TOKEN=changeme/MAPEO_API_TOKEN=${new_token}/" "${env_file}.tmp"
    info "Se ha generado un MAPEO_API_TOKEN aleatorio para esta instancia."
  else
    warn "No se encontró el placeholder MAPEO_API_TOKEN=changeme en la configuración. Si no es intencionado, el token podría estar ausente o hardcodeado."
  fi
  
  mv "${env_file}.tmp" "$env_file"
}

## @fn print_summary()
## @brief Imprime la tabla resumen de credenciales y URLs
print_summary() {
  set +u # Permitir variables no definidas temporalmente
  source "${ROOT_DIR}/moodle-matrix-dev/.env"
  set -u
  
  echo ""
  echo "=== RESUMEN DE SERVICIOS (Fase 1) ==="
  echo "Servicio    URL                              Credenciales"
  echo "----------------------------------------------------------------"
  echo "Moodle      http://localhost:${MOODLE_PUERTO_HOST:-8000}           ${MOODLE_USERNAME:-admin} / ${MOODLE_PASSWORD:-adminpass123}"
  echo "Matrix      http://localhost:${SYNAPSE_PUERTO_HOST:-8008}           -"
  echo "Element     http://localhost:${ELEMENT_PUERTO_HOST:-8081}           -"
  echo "Maubot      http://localhost:${MAUBOT_PUERTO_HOST:-29317}          -"
  echo "Doxygen     http://localhost:8005            -"
  echo "Mapeo API   http://mapeo-api:8000            (Solo red interna Docker. Token: ${MAPEO_API_TOKEN})"
  
  cd "${ROOT_DIR}/moodle-matrix-dev" || true
  if docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "ollama"; then
    echo "Ollama      http://localhost:${LLM_SERVER_OPCIONAL_PUERTO_HOST:-11434}          (Perfil Activo)"
  else
    echo "Ollama      -                                (Inactivo. Usa --ollama para levantar)"
  fi
  cd "${ROOT_DIR}"
  
  echo "----------------------------------------------------------------"
  echo "Proveedores LLM configurados en config/config.yaml."
  echo ""
}

# ------------------------------------------------------------------------------
# Stubs de fases futuras
# ------------------------------------------------------------------------------

## @fn cmd_up()
## @brief Levanta la infraestructura de Fase 1
cmd_up() {
  local use_ollama=false
  for arg in "$@"; do
    if [[ "$arg" == "--ollama" ]]; then
      use_ollama=true
    fi
  done
  
  generate_env
  
  info "Levantando servicios Docker Compose..."
  cd "${ROOT_DIR}/moodle-matrix-dev"
  
  if [ "$use_ollama" = true ]; then
    info "Perfil Ollama activado."
    docker compose --env-file .env --profile ollama up -d
  else
    docker compose --env-file .env up -d
  fi
  
  info "Esperando a que Moodle y mapeo-api estén operativos (Healthchecks)..."
  # Leer el nombre del contenedor dinámico
  local moodle_container=$(grep MOODLE_NOMBRE_CONTENEDOR .env | cut -d= -f2 || echo "moodle-matrix-dev-moodle-1")
  local mapeo_api_container=$(grep MAPEO_API_NOMBRE_CONTENEDOR .env | cut -d= -f2 || echo "moodle-matrix-dev-mapeo-api-1")
  
  while true; do
    local m_status=$(docker inspect --format="{{if .State.Health}}{{.State.Health.Status}}{{end}}" "$moodle_container" 2>/dev/null || echo "starting")
    local api_status=$(docker inspect --format="{{if .State.Health}}{{.State.Health.Status}}{{end}}" "$mapeo_api_container" 2>/dev/null || echo "starting")
    
    if [[ "$m_status" == "healthy" && "$api_status" == "healthy" ]]; then
      ok "Moodle y mapeo-api están operativos."
      break
    fi
    
    if [[ "$m_status" == "unhealthy" ]]; then
      error "Moodle falló el healthcheck. Revisa 'docker logs $moodle_container'."
    fi
    
    if [[ "$api_status" == "unhealthy" ]]; then
      error "mapeo-api falló el healthcheck. Revisa 'docker logs $mapeo_api_container'."
    fi
    
    sleep 5
  done
  
  cd "${ROOT_DIR}"
  print_summary
}
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
