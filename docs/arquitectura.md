# Arquitectura y Diseño

## Diseño de Aislamiento Estricto y Proveedores Modulares

El sistema aísla la información de cada alumno para evitar contaminación cruzada de datos (LLM hallucination) y preservar la estricta privacidad del estudiante.

- **Asignación 1:1**: 1 Alumno <--> 1 Repo (generado desde template) <--> 1 Sala Matrix.
- **Configuración centralizada**: Las claves de configuración y elección de proveedores residen en `config/config.yaml`. La elección del proveedor Git se hace con `git.proveedor_activo`.
- **Lectura Restringida**: Maubot opera bajo credenciales limitadas exclusivamente al repositorio vinculado a la sala de ejecución, impidiendo el acceso a repositorios de otros estudiantes.
- **Git Modular**: Se usa una capa de abstracción `GitProviderFactory`. Los proveedores operativos son GitHub y GitLab (vía estrategia fork+delete). Existe un módulo `self_hosted_provider.py` que actúa como un STUB (lanzará un error documentado), no funcional actualmente por diseño.

Para más detalles, revisa las \subpage decisiones-tecnicas "Decisiones Técnicas".

Para la explicación detallada de por qué usamos "generado desde template" en lugar de "fork", ver \subpage mapeo-alumno-repositorio.md "Modelo Alumno-Repositorio".

## Diagrama de Arquitectura Global

```mermaid
flowchart TD
    %% Entidades Externas
    Docente[Docente en Moodle]
    Alumno[Alumno en Matrix Chat]

    %% Sistemas Principales
    Moodle[Moodle Block BDC]
    MapeoAPI[Mapeo API]
    MariaDB[(MariaDB)]
    Matrix[Matrix Synapse]
    Maubot[Maubot LLM Bot]
    Redis[(Redis)]

    %% Workers
    SyncWorker1[Sync Worker 1]
    SyncWorker2[Sync Worker 2]

    %% Git Provider Abstraction
    subgraph GitProvider [Proveedor Git Modular]
        Factory[GitProviderFactory]
        GitHub[GitHub Provider]
        GitLab[GitLab Provider]
        SelfHosted[SelfHosted STUB\nNo Funcional]
        Factory --> GitHub
        Factory --> GitLab
        Factory --> SelfHosted
    end

    %% Repositorios
    subgraph Repositorios
        RepoOficial[Repo Oficial de la Asignatura]
        RepoAlumno[Repo del Alumno\n(generado desde template)]
    end

    %% Flujo 1: Creación BDC
    Docente -->|Inicia creación BDC| Moodle
    Moodle -->|Llama API POST /mapeos| MapeoAPI
    MapeoAPI -->|Usa configuración Git| Factory
    Factory -->|Aprovisiona repositorio| RepoAlumno
    RepoOficial -.->|Template| RepoAlumno
    MapeoAPI -->|Persiste Mapeo| MariaDB
    MapeoAPI -->|Crea sala e invita bot| Matrix

    %% Flujo 2: Chat en vivo
    Matrix <-->|Chat| Alumno
    Matrix <-->|Chat| Maubot

    %% Flujo 3: Sincronización Ascendente (Fase 5.1)
    RepoOficial -- Webhook push --> MapeoAPI
    MapeoAPI -->|POST /sync/oficial-updated\nEncola sync-job| Redis
    Redis -->|Consume sync-jobs| SyncWorker1
    Redis -->|Consume sync-jobs| SyncWorker2
    SyncWorker1 -->|Actualiza carpeta material-oficial/| RepoAlumno
    SyncWorker2 -->|Actualiza carpeta material-oficial/| RepoAlumno

    %% Flujo 4: Registro de Interacciones y Locking (Fase 6)
    Maubot -->|Encola log-job| Redis
    Redis -->|Consume log-jobs| SyncWorker1
    Redis -->|Consume log-jobs| SyncWorker2
    SyncWorker1 -.->|Lock distribuido Redis\nGit Push| RepoAlumno
    SyncWorker2 -.->|Lock distribuido Redis\nGit Push| RepoAlumno
```

## Mapa de Servicios (Puertos)

Las credenciales reales dependerán del proveedor que tengas activo (por ejemplo, si activas GitHub, no usarás GitLab).

| Servicio | Puerto Contenedor | Puerto Host | Credencial o Variable Clave | Notas |
|---|---|---|---|---|
| **Moodle** | 8080 | 8000 | `MOODLE_USERNAME` / `MOODLE_PASSWORD` | Usa credenciales definidas en `.env` al levantarse. |
| **Mapeo API** | 8000 | (Interno) | `MAPEO_API_TOKEN` | Generado automáticamente. |
| **MariaDB** | 3306 | 3306 | `MARIADB_USER` / `MARIADB_PASSWORD` | DB central para la API. |
| **Synapse** | 8008 | 8008 | `MATRIX_ACCESS_TOKEN` | Token admin. |
| **Element Web** | 80 | 8081 | - | Cliente web de Matrix en http://localhost:8081 |
| **Maubot** | 29317 | 29317 | `MATRIX_BOT_USER` | Backend de ejecución del LLM Bot. |
| **Doxygen** | 8000 | 8005 | - | Servidor de documentación en http://localhost:8005 |
| **Redis** | 6379 | 6379 | - | Broker de trabajos (sync y logs). |
| **Sync Worker 1 / 2** | N/A | N/A | - | Workers consumiendo RQ `sync-jobs` y `log-jobs`. |
| **GitHub** (Activo por defecto) | N/A | N/A | `GITHUB_PAT` | El `pat_env_var` configurado en `config.yaml`. |
| **GitLab** | N/A | N/A | `GITLAB_TOKEN` (ejemplo) | Se usaría si `git.proveedor_activo` = `gitlab`. |
| **Ollama** | 11434 | 11434 | `OLLAMA_API_KEY_DUMMY` | **Opcional**, requiere `./instalar.sh up --ollama`. |
