# Backup y Recuperación de Desastres

Este documento detalla la estrategia de copias de seguridad de la Fase 9.2, los elementos respaldados y el procedimiento exacto de restauración en caso de desastre.

## ¿Qué se respalda?
- **PostgreSQL (`mapeo_db`)**: Base de datos de producción que contiene el registro crítico del mapeo de los repositorios de alumnos y salas de Matrix asociadas a cursos de Moodle.
- **Redis (AOF)**: Volcado del registro *Append Only File* de Redis (`appendonlydir`). Es fundamental mantener el estado de las colas de trabajos en segundo plano (`rq:queue:sync-jobs` y `rq:queue:log-jobs`) para evitar perder sincronizaciones encoladas si se cae el sistema.

## ¿Qué NO se respalda y por qué?
- **Repositorios de Alumnos y Profesor (Oficial)**: Los repositorios en sí mismos no se respaldan localmente en este servidor porque la fuente de verdad y el respaldo natural de este código residen en el servidor Git remoto (GitHub/GitLab/Self-Hosted). Realizar un backup local solo generaría redundancia innecesaria y saturaría el almacenamiento.

## Política de Retención
Los backups se generan diariamente a las **03:00 am** a través del contenedor `backup` (Alpine Linux con `crond`). 
La política de retención local configurada en `scripts/backup.sh` es la siguiente:
- Se conservan todos los backups diarios de los **últimos 7 días**.
- Se conserva **1 backup semanal** (los generados el domingo) para las **últimas 4 semanas** (hasta 30 días de antigüedad).
- Backups con más de 30 días se eliminan automáticamente.

Los backups se almacenan en la carpeta `/backups` del repositorio, montada mediante un *bind mount* hacia el disco físico del servidor host.

---

## Procedimiento de Restauración (Probado en Fase 9.2)

> [!CAUTION]
> Los siguientes comandos sobrescribirán los datos actuales de la base de datos y de Redis. Utilizar solo en caso de desastre.

Asegúrate de ejecutar estos comandos en el directorio raíz del proyecto (`llm-wiki-assistant/moodle-matrix-dev`).

### 1. Detener los servicios
Detenemos todos los servicios que consumen o modifican las bases de datos:
```bash
docker compose stop postgres redis mapeo-api sync-worker-1 sync-worker-2 backup
```

### 2. Restaurar PostgreSQL
Asumiendo que has identificado el fichero de dump correcto en la carpeta `backups` (ej. `mapeo_20260802_075223.dump`), ejecuta:
```bash
# Iniciar temporalmente solo postgres
docker compose start postgres

# Ejecutar pg_restore limpiando la base de datos (-c) desde el contenedor de backup
docker exec -e PGPASSWORD=mapeo_db_pass moodle-matrix-dev-backup-1 pg_restore -h postgres -U mapeo_user -d mapeo_db -c -1 /backups/mapeo_20260802_075223.dump
```

### 3. Restaurar Redis (AOF)
Para restaurar el estado de las colas, debemos limpiar el volumen de datos de Redis e inyectar el directorio `appendonlydir` del archivo `.tar.gz`:

```bash
# Limpiar el appendonlydir actual
docker run --rm -v moodle-matrix-dev_redis_data:/data alpine sh -c "rm -rf /data/appendonlydir/*"

# Extraer el tar.gz en el volumen de datos de redis usando un contenedor temporal
# NOTA: Reemplazar redis_20260802_075223.tar.gz por el nombre del backup
bash -c "cat ../backups/redis_20260802_075223.tar.gz | docker run -i --rm -v moodle-matrix-dev_redis_data:/data alpine tar -xzf - -C /data"

# Ajustar los permisos (Redis usa uid/gid 999)
docker run --rm -v moodle-matrix-dev_redis_data:/data alpine chown -R 999:1000 /data/appendonlydir
```

### 4. Reiniciar los servicios
Una vez restaurados ambos almacenes de datos, reiniciar toda la pila tecnológica:
```bash
docker compose up -d
```
El sistema debe estar totalmente operativo conservando el mapeo y los trabajos que quedaron encolados.
