# Arquitectura del Sistema

El proyecto implementa un modelo de aislamiento estricto por alumno.

## Modelo 1:1 Alumno - Fork - Sala Matrix

1. **Repo Maestro**: Basado en `BdC-template` en GitHub.
2. **Fork por Alumno**: Cada estudiante dispone de su propio fork.
3. **Sala Matrix 1:1**: Sala privada en Synapse vinculada al alumno.
4. **Bot Maubot**: Atiende la sala y consulta **exclusivamente** el fork del alumno vinculado.

## Puertos de Servicios

Los puertos están definidos centralmente en `config/config.yaml`:

| Servicio | Puerto Host | Puerto Contenedor | Descripción |
| :--- | :--- | :--- | :--- |
| **Moodle** | `8000` | `8080` | LMS principal |
| **MariaDB** | `3306` | `3306` | Base de datos Moodle |
| **Synapse** | `8008` | `8008` | Matrix Homeserver |
| **Element Web** | `8081` | `80` | Cliente Web Matrix |
| **Maubot** | `29317` | `29317` | Motor de Bots |
| **MkDocs** | `8005` | `8000` | Servidor de Documentación |
| **Ollama (Opcional)** | `11434` | `11434` | Inferencia LLM local opcional |
