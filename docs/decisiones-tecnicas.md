\page decisiones_tecnicas Decisiones Técnicas

# Decisiones Técnicas

Este documento detalla las decisiones arquitectónicas clave tomadas durante el desarrollo de LLM Wiki Assistant.

## Fase 4.2: Abstracción del Proveedor Git

Para permitir que el proyecto no dependa exclusivamente de GitHub, se extrajo la interacción con repositorios detrás de la interfaz `GitProviderClient`. 

### Por qué "Fork + Delete" en GitLab
Aunque GitLab dispone de una API de Exportación/Importación de proyectos, se optó por la estrategia de:
1. Hacer un fork del repositorio oficial de la asignatura.
2. Inmediatamente hacer un `DELETE` a la relación de fork (`/projects/:id/fork`).

Esta decisión se tomó para **replicar la semántica de GitHub** (donde se usa la generación desde un template). Esta aproximación es síncrona y escala mejor para picos de matriculación, evitando los tiempos de espera inherentes a procesos asíncronos pesados como la exportación e importación, y asegurando que los alumnos tengan un repositorio independiente y limpio.

### Proveedor Autoalojado (Self-Hosted)
La universidad dispone de un servidor autoalojado gestionado por la OSL. Al no conocer a priori la tecnología exacta (Gitea, Forgejo, GitLab CE/EE), se ha preparado el terreno:
- Si resulta ser **GitLab CE/EE**, basta con utilizar el `gitlab_provider.py` apuntando a la URL interna.
- Si es **Gitea/Forgejo**, se creará la lógica nativa en `self_hosted_provider.py` consumiendo su endpoint `/generate`.

Hasta su definición final, `SelfHostedProvider` lanza un `NotImplementedError` estructurado para que el futuro equipo sepa exactamente dónde inyectar el código.

### Introducción de Alembic
Inicialmente, los modelos de base de datos se generaban mediante `Base.metadata.create_all()` y se consideró usar scripts simples para migrar SQLite. Sin embargo, para preparar el sistema para su uso real en producción:
- Se optó por **Alembic**.
- Aprovechando que los datos en Fase 4 eran efímeros, se decidió borrar la base de datos de pruebas inicial y generar una migración **baseline**.
- Esto garantiza que cualquier futuro cambio al modelo de datos dispondrá ya de una infraestructura de migración funcional (ejecutada automáticamente al arrancar el contenedor en `Dockerfile`).
