#!/bin/bash
set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "[INFO] Iniciando backup: $TIMESTAMP"

# 1. Backup de PostgreSQL
PG_BACKUP_FILE="$BACKUP_DIR/mapeo_${TIMESTAMP}.dump"
echo "[INFO] Generando backup de PostgreSQL en $PG_BACKUP_FILE..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h postgres -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc -f "$PG_BACKUP_FILE"

# 2. Backup de Redis (AOF Directory)
REDIS_BACKUP_FILE="$BACKUP_DIR/redis_${TIMESTAMP}.tar.gz"
echo "[INFO] Generando backup del AOF de Redis en $REDIS_BACKUP_FILE..."
# Asumiendo que redis_data se monta en /redis_data en este contenedor de backup
if [ -d "/redis_data/appendonlydir" ]; then
    tar -czf "$REDIS_BACKUP_FILE" -C /redis_data appendonlydir
else
    echo "[WARN] Directorio appendonlydir no encontrado en /redis_data. Verifique que AOF está habilitado."
    # Back up the whole data dir if appendonlydir is missing, just in case
    tar -czf "$REDIS_BACKUP_FILE" -C / redis_data
fi

echo "[INFO] Backups generados correctamente."

# 3. Política de Retención
echo "[INFO] Aplicando política de retención..."

# Conservar los últimos 7 backups diarios (cualquier backup menor a 7 días se guarda)
# Para semanas, podemos buscar backups antiguos.
# Una manera robusta y sencilla usando `find`:
# Borrar todos los backups que tengan más de 7 días, PERO conservar 1 backup por semana.
# Como puede ser complejo con `find`, un enfoque sencillo para la retención:
# 1. Borrar todos los archivos de más de 30 días.
# 2. De los archivos entre 7 y 30 días de antigüedad, mantener solo los que caigan en un día específico de la semana (ej. Domingo).

# Eliminamos ficheros más antiguos de 30 días (las últimas 4 semanas de margen)
find "$BACKUP_DIR" -type f -name "mapeo_*.dump" -mtime +30 -exec rm {} \;
find "$BACKUP_DIR" -type f -name "redis_*.tar.gz" -mtime +30 -exec rm {} \;

# Para los ficheros que tienen entre 7 y 30 días, si no se generaron un Domingo (día 7 de la semana), los borramos.
# find $BACKUP_DIR -mtime +7 -mtime -30. Iteramos.
for file in "$BACKUP_DIR"/mapeo_*.dump "$BACKUP_DIR"/redis_*.tar.gz; do
    if [ -f "$file" ]; then
        # Verificar si tiene más de 7 días
        if [ $(find "$file" -mtime +7 -print) ]; then
            # Obtener el día de la semana en el que se creó/modificó el archivo (1-7, 7 es Domingo)
            # Linux date de stat
            file_ts=$(stat -c %Y "$file")
            file_dow=$(date -d "@$file_ts" +%u)
            if [ "$file_dow" -ne 7 ]; then
                echo "Eliminando backup antiguo no semanal: $file"
                rm -f "$file"
            fi
        fi
    fi
done

echo "[INFO] Proceso de backup finalizado exitosamente."
