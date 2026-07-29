#!/usr/bin/env bash
# ==============================================================================
# instalar.sh — Punto de entrada único de llm-wiki-assistant
# ==============================================================================
# Uso:
#   ./instalar.sh                  → instalación/arranque completo automático
#   ./instalar.sh help             → lista todos los subcomandos
#   ./instalar.sh docs serve       → levanta MkDocs en el puerto configurado
#   ./instalar.sh docs check       → verifica la documentación (--strict)
#   ./instalar.sh up               → (Fase 1) levanta el stack Docker Compose
#   ./instalar.sh down             → (Fase 1) para el stack Docker Compose
#   ./instalar.sh logs [servicio]  → (Fase 1) muestra logs de un servicio
#   ./instalar.sh git setup        → (Fase 1) configura repositorios GitHub
#   ./instalar.sh bot sync         → (Fase 3) sincroniza sala-fork en Maubot
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${ROOT_DIR}/config/config.yaml"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
ok()    { echo "[ OK ]  $*"; }
warn()  { echo "[WARN]  $*"; }
skip()  { echo "[SKIP]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

check_docker() {
  command -v docker &>/dev/null || error "Docker no está instalado. Instálalo antes de continuar: https://docs.docker.com/get-docker/"
}

# Lee una clave hoja de config.yaml (grep simple, no parser YAML completo)
yaml_get() {
  local key="$1" default="${2:-}"
  local value
  value=$(grep -m1 "${key}:" "${CONFIG_FILE}" 2>/dev/null \
    | awk -F': ' '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); gsub(/"/, "", $2); print $2}' || true)
  echo "${value:-$default}"
}

# Copia fichero .example → real solo si el real no existe aún
copy_if_missing() {
  local src="$1" dst="$2"
  if [[ -f "$dst" ]]; then
    skip "$(basename "$dst") ya existe, no se sobreescribe."
  else
    cp "$src" "$dst"
    ok "$(basename "$dst") creado desde $(basename "$src")."
    warn "  Edita ${dst} y rellena los secretos reales antes de continuar."
  fi
}

# ------------------------------------------------------------------------------
# Ayuda
# ------------------------------------------------------------------------------
usage() {
  cat <<EOF
LLM Wiki Assistant — instalar.sh

Uso: ./instalar.sh [comando] [opciones]

  (sin argumentos)         Instalación completa automática
  help                     Muestra esta ayuda

  docs serve               Levanta MkDocs en http://localhost:PUERTO_DOCS
  docs check               Verifica la documentación (mkdocs build --strict)

  up                       (Fase 1) Levanta el stack Docker Compose
  down [--volumes]         (Fase 1) Para el stack
  logs [servicio]          (Fase 1) Muestra logs
  status                   (Fase 1) Estado de los contenedores

  git setup                (Fase 1) Configura repositorios GitHub
  bot sync                 (Fase 3) Sincroniza sala Matrix -> fork GitHub
EOF
  exit 0
}

# ------------------------------------------------------------------------------
# Flujo de instalación completo (sin argumentos)
# ------------------------------------------------------------------------------
cmd_install_all() {
  echo ""
  echo "=== LLM Wiki Assistant — Instalación Automática ==="
  echo "    Directorio raíz: ${ROOT_DIR}"
  echo ""

  # Paso 1: Secretos y configuración (no requiere Docker)
  echo "--- Paso 1 / 3: Configuración y secretos ---"
  copy_if_missing "${ROOT_DIR}/.env.example"                                      "${ROOT_DIR}/.env"
  copy_if_missing "${ROOT_DIR}/config/config.yaml.example"                        "${ROOT_DIR}/config/config.yaml"
  copy_if_missing "${ROOT_DIR}/moodle-matrix-dev/maubot/base-config.yaml.example" "${ROOT_DIR}/moodle-matrix-dev/maubot/base-config.yaml"
  copy_if_missing "${ROOT_DIR}/moodle-matrix-dev/maubot/config.yaml.example"      "${ROOT_DIR}/moodle-matrix-dev/maubot/config.yaml"
  echo ""

  # Paso 2: Stack Docker (Fase 1, aún no implementado)
  echo "--- Paso 2 / 3: Entorno Docker ---"
  warn "Stack Docker (Fase 1 pendiente). Cuando esté implementado: ./instalar.sh up"
  echo ""

  # Paso 3: Verificación de documentación (requiere Docker)
  echo "--- Paso 3 / 3: Verificando documentación ---"
  check_docker
  local docs_port; docs_port=$(yaml_get "puerto_host" "8005")
  info "Ejecutando mkdocs build --strict..."
  docker run --rm -v "${ROOT_DIR}:/docs" squidfunk/mkdocs-material build --strict
  ok "Documentación verificada sin warnings."
  echo ""

  echo "=== Instalación completada ==="
  echo "  [OK] Ficheros de configuración listos"
  echo "  [ ] Stack Docker   (Fase 1 pendiente)"
  echo "  [OK] Documentación verificada"
  echo ""
  echo "  Levanta la documentación con: ./instalar.sh docs serve"
  echo "                 Disponible en: http://localhost:${docs_port}"
  echo ""
}

# ------------------------------------------------------------------------------
# Documentación
# ------------------------------------------------------------------------------
cmd_docs() {
  local submode="${1:-serve}"
  check_docker
  local docs_port; docs_port=$(yaml_get "puerto_host" "8005")

  case "$submode" in
    serve|start|dev)
      info "Levantando MkDocs en http://localhost:${docs_port} ..."
      docker run --rm -it -p "${docs_port}:8000" -v "${ROOT_DIR}:/docs" squidfunk/mkdocs-material
      ;;
    check|build|verify)
      info "Ejecutando mkdocs build --strict..."
      docker run --rm -v "${ROOT_DIR}:/docs" squidfunk/mkdocs-material build --strict
      ok "Documentación verificada sin warnings."
      ;;
    *)
      error "Sub-comando docs desconocido: '${submode}'. Usa 'serve' o 'check'."
      ;;
  esac
}

# ------------------------------------------------------------------------------
# Stubs de fases futuras
# ------------------------------------------------------------------------------
cmd_up()     { error "'up' aún no está implementado (Fase 1 pendiente)."; }
cmd_down()   { error "'down' aún no está implementado (Fase 1 pendiente)."; }
cmd_logs()   { error "'logs' aún no está implementado (Fase 1 pendiente)."; }
cmd_status() { error "'status' aún no está implementado (Fase 1 pendiente)."; }
cmd_git()    { error "'git setup' aún no está implementado (Fase 1 pendiente)."; }
cmd_bot()    { error "'bot sync' aún no está implementado (Fase 3 pendiente)."; }

# ------------------------------------------------------------------------------
# Punto de entrada
# ------------------------------------------------------------------------------
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
    *) error "Comando desconocido: '${cmd}'. Ejecuta './instalar.sh help' para ver la ayuda." ;;
  esac
}

main "$@"
