# Sincronización Upstream y Rate Limiting

El proceso de sincronización permite mantener los repositorios de los estudiantes al día con las actualizaciones del repositorio oficial del profesor. 

Cuando el profesor hace push a su repositorio, un webhook dispara una petición a `mapeo-api` que encola trabajos asíncronos (`sync-jobs`) para cada alumno.

## Manejo de Rate Limiting (Límite de Peticiones)

Dada la naturaleza masiva de la sincronización en cursos grandes, es posible alcanzar los límites de la API de GitHub o GitLab, especialmente los límites secundarios (Abuse Detection) debido a ráfagas rápidas de creación de repositorios o pushes simultáneos.

Hemos implementado un manejo explícito para distinguir errores genéricos de red (que usan un backoff de reintento estándar) de errores de limitación de tasa (que requieren esperar un tiempo específico dictado por la plataforma o un backoff conservador).

### Arquitectura de Detección

Existen dos capas donde se detecta el rate limiting, cada una con un nivel de precisión distinto por limitaciones inherentes de los clientes subyacentes:

1. **Capa `mapeo-api` (Precisión Alta - HTTP Real)**:
   - Utiliza `httpx` para hacer peticiones directas a la API REST de GitHub/GitLab (por ejemplo, para generar repositorios desde plantillas).
   - Al ser un cliente HTTP completo, si se excede el límite (403/429), extrae los tiempos exactos de espera directamente de las cabeceras `Retry-After` (límite secundario) o `X-RateLimit-Reset` (límite primario) y reencola dinámicamente o bloquea la llamada sincrónica según corresponda.

2. **Capa `maubot` / Sync Worker (Mejor Esfuerzo - Cliente Git)**:
   - Las tareas de sincronización (en `tasks.py`) utilizan el cliente binario nativo `git` (`git fetch`/`git push` sobre HTTPS).
   - El ejecutable `git` intercepta y descarta las cabeceras HTTP reales devolviendo sólo un texto en `stderr` (por ejemplo, `429 Too Many Requests`). GitHub **no** expone el tiempo exacto de reintento para operaciones git sobre HTTPS en `/rate_limit`.
   - Por esta razón técnica y no por falta de implementación, se aplica un **backoff conservador específico** (exponencial: 60s, 120s, 240s... con tope máximo) cuando se detecta el fallo por rate limit en la salida de consola de git.
   - Como señal complementaria oportunista, si `/rate_limit` devuelve que el límite primario se ha agotado, se utiliza ese timestamp de reseteo si es mayor al backoff calculado.

### Separación de Código y Excepciones
Para mantener el aislamiento arquitectónico entre contenedores, la excepción `GitHubRateLimitError` se comparte estructuralmente, pero se implementa de manera independiente en ambos subsistemas (`mapeo-api` y `maubot`). Esta separación está documentada y responde a los mecanismos dispares de detección explicados arriba.
