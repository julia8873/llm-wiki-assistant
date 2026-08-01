# Logging de Interacciones (Fase 6)

## Diferencia de Propósito

El proyecto cuenta con tres carpetas de registro distintas para mantener la separación de responsabilidades:

1. `logs/log.txt`: Escrito exclusivamente por el proceso de sincronización asíncrona (Fase 5.1). Deja constancia de cuándo el repositorio oficial del profesor ha sido replicado en el repositorio del alumno.
2. `bitacora/log.md`: Modificado exclusivamente por los flujos RAG/OKF locales (comando `!deshacer`). Registra operaciones manuales de ingesta o eliminación de conocimiento (Fase 5).
3. **`logs/interacciones/YYYY-MM-DD.jsonl` (NUEVO)**: Gestionado por la cola `log-jobs` de manera asíncrona. Registra todas las preguntas y respuestas entre el alumno y el bot, incluyendo el conocimiento extraído (rutas de ficheros recuperados), garantizando la trazabilidad analítica de la plataforma sin ensuciar los logs de comandos o el RAG.

## Mecanismo de Cerrojo Distribuido (Distributed Lock)

Con el objetivo de evitar una corrupción del árbol Git en el escenario donde se encola un log asíncrono y, simultáneamente, se dispara una sincronización completa del repositorio que hace un reset duro o manipula los índices de git locales, se ha implementado un mutex estricto.

### Características del Lock

- **Implementación**: `contextlib.asynccontextmanager` encapsulando un cliente nativo `redis.asyncio`.
- **Clave**: `repo_lock:{ruta_local_del_repositorio}`. Se aplica al path físico local, garantizando que procesos que operan sobre la misma carpeta colisionan y se encolan, sin bloquear interacciones de otros alumnos en el mismo nodo worker.
- **Heartbeat & TTL**: El TTL base inicial está calibrado en **60 segundos**, basado en pruebas reales de red (clonación limpia sobre GitHub tardando ~1.6s). Además, incluye una tarea en background (*heartbeat*) que ejecuta un `lock.extend(ttl)` cada **20s**. Esto previene tajantemente la liberación prematura si la red de GitHub es ahogada por *rate limits*.
- **Backoff en Reintentos (Inline Blocking)**: El cerrojo está configurado con un `blocking_timeout` de 30 segundos. Si otro hilo está operando sobre el árbol Git, el proceso se quedará esperando dócilmente. Si el tiempo de espera se excede, lanza `LockAcquisitionError`, permitiendo al demonio RQ capturar la excepción y aplicar su configuración nativa para re-encolar de forma idempotente en el futuro.

## Escalado de Workers

Se ha configurado Docker Compose explícitamente con dos servicios gemelos (`sync-worker-1` y `sync-worker-2`) que escuchan ambas colas (`sync-jobs`, `log-jobs`). 
**Decisión Técnica**: Se evita la sintaxis de Swarm (`deploy.replicas: 2`) ya que un *compose up* simple la ignora silenciosamente. Esta redundancia absorbe ráfagas altas, garantizando la responsividad del bot sin congelar un solo worker para toda la institución. Si se requieren más recursos en producción, la vía de escalado directa es desacoplar `log-jobs` a su propio contenedor.

## Idempotencia y Tolerancia a Fallos

Si el último paso del proceso de logs (`git push`) falla por latencia de red, la tarea será relanzada por RQ en diferido. La función compara el hash SHA-256 de la nueva línea a inyectar contra el contenido existente local (si el commit anterior se completó con éxito) y salta el `commit` duplicado, dirigiéndose directamente a un nuevo intento de `push`.
Esto evita generar múltiples registros idénticos por fallos puramente transaccionales. Además, el broker Redis goza de persistencia AOF que salva cualquier encolado de logs frente a crasheos del contenedor.
