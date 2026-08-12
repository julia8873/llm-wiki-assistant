# LLM Wiki Assistant

Sistema integrado de docencia Moodle-Matrix-GitHub.

## Componentes Core
- **Moodle (LMS)**: Gestiona matriculaciones y orquesta la creación de repositorios.
- **GitHub**: Almacena repositorios (forks) individuales en Open Knowledge Format (OKF).
- **Matrix/Synapse**: Provee salas de chat 1:1.
- **Maubot (LLM Wiki Assistant)**: Agente LLM que atiende consultas basándose exclusivamente en el repositorio asignado a la sala.

## Fases de Implementación y Resumen de Estado
Puedes consultar el histórico detallado y las pruebas en el \subpage resumen_fases. Adicionalmente, si eres un asistente basado en LLM integrándose al proyecto, lee de forma obligatoria el \subpage contexto_ia.

| Fase | Descripción | Estado |
|---|---|---|
| 0.1 | Documentación Doxygen y Configuración Base | ✅ Completada |
| 1 | Infraestructura Docker Compose | ✅ Completada |
| 2 | Almacén de Mapeos (FastAPI + SQLite) | ✅ Completada |
| 3 | Bloque Moodle `block_bdc` | ✅ Completada |
| 4 | Provisionamiento GitHub y pruebas de integración | ✅ Completada |
| 5 | Plugin Maubot `llm-wiki-assistant` | ⏳ Pendiente |
