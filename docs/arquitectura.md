# Arquitectura y Diseño

## Diseño de Aislamiento Estricto
El sistema aísla la información de cada alumno para evitar contaminación cruzada de datos (LLM hallucination) y preservar la estricta privacidad del estudiante.

- **Asignación 1:1**: 1 Alumno <--> 1 Fork GitHub <--> 1 Sala Matrix.
- **Configuración centralizada**: El PAT de GitHub vive en `config/config.yaml` y se propaga automáticamente a `GITHUB_PAT` en el entorno Docker mediante `instalar.sh`, evitando duplicidades con `.env.example`.
- **Lectura Restringida**: Maubot opera bajo credenciales limitadas exclusivamente al fork vinculado a la sala de ejecución, impidiendo el acceso a repositorios de otros estudiantes.

## Mapa de Servicios (Puertos)
Definidos centralmente en `config/config.yaml`.

| Servicio | Host | Contenedor | Propósito |
|---|---|---|---|
| Moodle | `8000` | `8080` | Plataforma LMS principal. |
| MariaDB | `3306` | `3306` | Persistencia de datos Moodle. |
| Synapse | `8008` | `8008` | Servidor de mensajería Matrix. |
| Element Web | `8081` | `80` | Cliente web Matrix. |
| Maubot | `29317` | `29317` | Backend de ejecución del bot. |
| Doxygen | `8005` | `8000` | Servidor de documentación HTML. |
| Ollama | `11434` | `11434` | Inferencia LLM local (Opcional). |
