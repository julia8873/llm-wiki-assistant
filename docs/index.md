# LLM Wiki Assistant - Documentación del Proyecto

Bienvenido a la documentación oficial del entorno docente **LLM Wiki Assistant**.

## 📌 Visión General
Este sistema integra:
- **Moodle (LMS)**: Gestión de cursos y alumnos.
- **GitHub**: Repositorio maestro de asignatura y forks individuales por alumno en formato Open Knowledge Format (OKF).
- **Matrix / Element**: Salas de chat privadas 1:1 por alumno.
- **Maubot / LLM Wiki Assistant**: Bot conversacional acotado estrictamente a leer el fork del alumno de la sala actual.

## 🧭 Navegación de la Documentación
- [Arquitectura del Sistema](arquitectura.md): Descripción de componentes, diagramas e infraestructura.
- [Instalación y Despliegue](instalacion.md): Guía de despliegue local mediante Docker Compose.
- [Mapeo Alumno-Fork-Sala](mapeo-alumno-fork.md): Esquema de la tabla central `mdl_block_bdc_mapping`.
- [Bot Maubot](bot.md): Estado y especificación del plugin Maubot.
- [Seguridad y Credenciales](seguridad.md): Gestión de secretos y plantillas `.example`.

## ⚙️ Estado Actual del Proyecto
El proyecto se encuentra en la **Fase 0.1 (Documentación MkDocs y Configuración Base)**. Las fases de infraestructura Docker, desarrollo del bloque Moodle y plugin Maubot se completarán secuencialmente.
