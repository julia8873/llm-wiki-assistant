# LLM Wiki Assistant

Sistema integrado de docencia Moodle-Matrix-GitHub.

## Componentes Core
- **Moodle (LMS)**: Gestiona matriculaciones y orquesta la creación de repositorios.
- **GitHub**: Almacena repositorios (forks) individuales en Open Knowledge Format (OKF).
- **Matrix/Synapse**: Provee salas de chat 1:1.
- **Maubot (LLM Wiki Assistant)**: Agente LLM que atiende consultas basándose exclusivamente en el repositorio asignado a la sala.

## Fases de Implementación
| Fase | Descripción | Estado |
|---|---|---|
| 0.1 | Documentación Doxygen y Configuración Base | ✅ Completada |
| 1 | Infraestructura Docker Compose | ⏳ Pendiente |
| 2 | Bloque Moodle `block_bdc` | ⏳ Pendiente |
| 3 | Sincronización Moodle-Matrix-GitHub | ⏳ Pendiente |
| 4 | Pruebas Automáticas | ⏳ Pendiente |
| 5 | Plugin Maubot `llm-wiki-assistant` | ⏳ Pendiente |
