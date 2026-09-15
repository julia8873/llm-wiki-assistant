$ErrorActionPreference = "SilentlyContinue"

# Crear estructura base
New-Item -ItemType Directory -Force -Path src\api, src\bot, src\matrix\element, src\matrix\synapse-custom, src\matrix\synapse-data, src\moodle, src\shared, src\backup

# 1. API, Bot, Shared
Move-Item -Path moodle-matrix-dev\mapeo-api\* -Destination src\api\
Move-Item -Path moodle-matrix-dev\maubot\* -Destination src\bot\
Move-Item -Path shared-pkg\* -Destination src\shared\

# 2. Matrix
Move-Item -Path moodle-matrix-dev\synapse-custom\* -Destination src\matrix\synapse-custom\
Move-Item -Path moodle-matrix-dev\synapse-data\* -Destination src\matrix\synapse-data\
Move-Item -Path moodle-matrix-dev\element-config.json -Destination src\matrix\element\config.json
Move-Item -Path moodle-matrix-dev\default.conf.template -Destination src\matrix\element\default.conf.template
Move-Item -Path moodle-matrix-dev\homeserver.db -Destination src\matrix\synapse-data\

# 3. Moodle
Move-Item -Path moodle-matrix-dev\Dockerfile.moodle -Destination src\moodle\Dockerfile
Move-Item -Path block_bdc -Destination src\moodle\block_bdc
Move-Item -Path moodle-matrix-dev\moodle_plugins\* -Destination src\moodle\

# 4. Scripts y Backup container
Move-Item -Path moodle-matrix-dev\scripts\* -Destination scripts\
Move-Item -Path moodle-matrix-dev\backup\* -Destination src\backup\
Move-Item -Path moodle-matrix-dev\create_env.php -Destination scripts\create_env.php
Move-Item -Path moodle-matrix-dev\sync_moodle.php -Destination scripts\sync_moodle.php

# 5. docker-compose
Move-Item -Path moodle-matrix-dev\docker-compose.yml -Destination docker-compose.yml

# Limpiar directorios vacíos
Remove-Item -Path moodle-matrix-dev\mapeo-api, moodle-matrix-dev\maubot, moodle-matrix-dev\synapse-custom, moodle-matrix-dev\synapse-data, moodle-matrix-dev\moodle_plugins, moodle-matrix-dev\scripts, moodle-matrix-dev\backup, shared-pkg -Recurse -Force
Remove-Item -Path moodle-matrix-dev -Recurse -Force

Write-Output "Archivos movidos correctamente a la nueva estructura."
