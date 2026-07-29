#!/bin/bash
## @file configurar_bdc.sh
## @brief Wrapper Bash para invocar el aprovisionamiento de repositorios en GitHub.
## @details
## Recibe el nombre de la asignatura y una lista separada por comas de profesores.
## Utiliza la instalación local de Python para ejecutar el script núcleo (configurar_bdc_core.py).
##
## Ejemplo de uso:
## ./configurar_bdc.sh "Math101" "julia8873,profe2"

if [ "$#" -ne 2 ]; then
    echo "Uso: $0 <NombreAsignatura> <Profesor1,Profesor2,...>"
    exit 1
fi

ASIGNATURA=$1
PROFESORES=$2

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CORE_SCRIPT="$SCRIPT_DIR/configurar_bdc_core.py"

# Usar el Python local (requiere PyYAML y httpx instalados)
python3 "$CORE_SCRIPT" "$ASIGNATURA" "$PROFESORES"
