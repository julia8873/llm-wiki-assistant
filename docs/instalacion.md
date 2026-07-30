# Despliegue y Operación

## Script Orquestador: `instalar.sh`
Único punto de entrada para operaciones de infraestructura. 

### Instalación por Defecto
Ejecuta el ciclo de validación inicial y levanta la documentación:
```bash
./instalar.sh
```
Flujo de ejecución:
1. Verifica dependencias (Docker).
2. Clona plantillas de configuración (`.example` -> real).
3. Levanta el servidor de documentación Doxygen en modo *detached* (segundo plano).
4. Compila y empaqueta automáticamente el plugin del bot de Matrix en formato `.mbp` (Fase 5).

### Levantar la Infraestructura (Fase 1)
Para levantar el stack tecnológico de contenedores, utiliza el comando `up`:
```bash
./instalar.sh up [--ollama]
```
Flujo de ejecución interno:
1. **Autogeneración del Entorno**: El orquestador extrae dinámicamente puertos y nombres de contenedores desde `config/config.yaml` y los fusiona junto a tus secretos (`moodle-matrix-dev/.env.example`) dentro del archivo `moodle-matrix-dev/.env`.
2. **Levantamiento Docker**: Ejecuta `docker compose up -d`.
3. **Validación (Healthcheck)**: Realiza un *polling* sobre los contenedores clave (especialmente Moodle) esperando a que reporten estado "Healthy".
4. **Pruebas de Integración**: Se puede probar la respuesta HTTP final ejecutando `./moodle-matrix-dev/scripts/test-services.sh`.

### Ejecución sin entorno virtual
No necesitas crear un entorno virtual para trabajar con este proyecto. Desde la carpeta del microservicio puedes instalar las dependencias directamente con el intérprete del sistema:

```bash
cd moodle-matrix-dev/mapeo-api
python -m pip install -r requirements.txt
```

Luego puedes ejecutar la API o las pruebas con `python` sin depender de `venv`.

### Configuración del Motor LLM
El sistema permite cambiar en caliente entre 3 proveedores modificando el campo `llm.proveedor_activo` en `config/config.yaml`:
1. **`openai`** (por defecto): API externa (gpt-4o-mini). Ideal para producción.
2. **`gemini`**: API externa Google (gemini-1.5-flash). Ideal para producción.
3. **`ollama`**: Inferencia local. Soportado vía compatibilidad OpenAI nativa (`/v1/chat/completions`). **Nota importante**: Ollama está pensado para entornos aislados, offline o de prueba. No es el camino principal de producción debido al alto costo de inferencia local en CPU.

*Nota: El token de GitHub se obtiene desde `config/config.yaml` y se inyecta automáticamente como `GITHUB_PAT` en `moodle-matrix-dev/.env` por `instalar.sh`; no es necesario definirlo manualmente en los `.env.example`.*

### Inferencia Local (Ollama)
Si seleccionas `ollama` y deseas ejecutar el motor localmente mediante Docker, debes indicarlo explícitamente al levantar la infraestructura (ya que está apagado por defecto para ahorrar recursos):
```bash
./instalar.sh up --ollama
```
El script `instalar.sh` validará que, si se utiliza una instancia de Ollama instalada localmente (fuera de Docker), esta tenga al menos la **versión 0.3.0** instalada, que es la mínima requerida para disponer del endpoint `/v1/chat/completions` usado por el bot.

### Pruebas manuales en Moodle
Para validar el flujo completo desde la interfaz, es necesario iniciar sesión en Moodle y ejecutar la acción del bloque BDC desde un curso visible.

1. Acceder a Moodle como administrador.
2. Crear o abrir un curso de prueba.
3. Crear manualmente un usuario de prueba desde la interfaz de Moodle con los siguientes datos:
   - Nombre de usuario: `student1`
   - Contraseña: `Student1!`
   - Nombre completo: `Student One`
   - Correo electrónico: `student1@example.com`
4. Matricular ese usuario en el curso de prueba.
5. Iniciar sesión con ese usuario y ejecutar la acción del bloque.
6. Comprobar la creación del mapeo y del repositorio asociado.

> Nota: este usuario se ha creado manualmente en Moodle para realizar pruebas de integración del flujo actual.

### Comandos de Operación
| Comando | Acción |
|---|---|
| `./instalar.sh docs serve` | Levanta Doxygen en `http://localhost:8005`. |
| `./instalar.sh docs check` | Verifica consistencia de documentación (`WARN_AS_ERROR=YES`). Falla si hay enlaces rotos. |
| `./instalar.sh up [--ollama]` | Levanta stack Docker Compose (Fase 1). |
| `./instalar.sh down` | Detiene stack conservando volúmenes (Fase 1). |
| `./instalar.sh git setup` | Configura repositorios base (Fase 1). |
| `./instalar.sh bot sync` | Fuerza sincronización base de datos Moodle -> Matrix (Fase 3). |
| `./instalar.sh bot package` | Compila y empaqueta el plugin del bot en formato `.mbp` (Fase 5). |
