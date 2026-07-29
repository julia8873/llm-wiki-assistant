# Resumen Exhaustivo de Fases y Pruebas Realizadas {#resumen_fases}

Este documento técnico constituye el registro maestro, exhaustivo y detallado de todo el desarrollo, la toma de decisiones arquitectónicas, la infraestructura, los scripts de automatización y las pruebas automatizadas ejecutadas durante las Fases 0, 0.1, 1 y 2 del proyecto `llm-wiki-assistant`.

---

## Fase 0: Arquitectura Base y Estructuración
Durante esta fase inicial, se sentaron las bases lógicas y físicas del repositorio.

### Desarrollo e Implementación
- **Estructura de Directorios**: Se aislaron las responsabilidades del código estableciendo la siguiente jerarquía:
  - `config/`: Archivos globales de parametrización (ej. `config.yaml`).
  - `docs/`: Repositorio central de documentación técnica en Markdown.
  - `moodle-matrix-dev/`: Entorno de infraestructura Docker (contenedores, APIs, bots y utilidades de red).
- **Documentación Temática (Technical Writing)**: Redacción inicial de los manuales del sistema aplicando estrictamente normas de *Technical Writing Senior* (cero redundancia, enfoque en el "Por qué" y "Cómo"). Se crearon:
  - `arquitectura.md`: Visión global de cómo interactúan Moodle, Matrix, GitHub y Maubot.
  - `instalacion.md`: Requisitos previos y comandos de despliegue.
  - `seguridad.md`: Gestión de credenciales, exposición de puertos y aislamiento de red.
  - `mapeo-alumno-fork.md`: Definición conceptual de la persistencia de relaciones.
  - `bot.md`: Patrones de diseño para la futura interacción del LLM.

---

## Fase 0.1: Integración de Doxygen y Validación Estricta
Se configuró un pipeline de documentación robusto para procesar automáticamente los archivos del proyecto.

### Desarrollo e Implementación
- **Motor Doxygen**: Se creó y afinó el archivo `Doxyfile` en la raíz del proyecto.
  - `INPUT` configurado para rastrear directorios recursivamente (`docs`, `moodle-matrix-dev`, `README.md`).
  - Activada la bandera `WARN_AS_ERROR=YES`. Esta decisión de diseño garantiza que cualquier fallo de formato, enlace roto, o etiqueta Doxygen inválida aborte el proceso, asegurando calidad absoluta en CI/CD.
  - Exclusión de carpetas basura o entornos virtuales (`*/venv/*`, `*/__pycache__/*`).
- **Orquestador (`instalar.sh`)**:
  - Comando `./instalar.sh docs check`: Invoca a Doxygen en modo de comprobación estricta de validación y termina.
  - Comando `./instalar.sh docs serve`: Invoca a Doxygen y levanta un micro-contenedor en segundo plano (basado en imagen Python ligera) sirviendo estáticos mediante `http.server` expuesto localmente en http://localhost:8005.

### Pruebas Realizadas
- **Test de Compilación Estricta**: Múltiples ejecuciones garantizando que no se emitieran advertencias de parseo en Markdown.
- **Test de Puerto**: Accesibilidad del puerto 8005 verificado manualmente.

---

## Fase 1: Infraestructura Docker y Automatización
Esta fase se centró en unificar el ecosistema bajo un mismo orquestador para un despliegue idempotente de "un solo clic".

### Desarrollo e Implementación
- **Stack Tecnológico (Docker Compose)**: Definición del `moodle-matrix-dev/docker-compose.yml` integrando:
  - `moodle` (Bitnami Moodle `latest`): LMS principal expuesto en puerto 8000.
  - `mariadb` (MariaDB `10.11`): Backend de datos para Moodle.
  - `synapse` (Matrix.org Synapse): Servidor federable de Matrix expuesto en 8008.
  - `element`: Cliente web para Synapse en 8081.
  - `maubot`: Core del asistente LLM expuesto internamente.
  - `ollama`: Implementado bajo el perfil condicional `profiles: ["ollama"]` para ofrecer IA generativa local.
- **Orquestación Inteligente en Bash (`instalar.sh`)**:
  - **Generador Dinámico de Configuración**: Un algoritmo que lee `config/config.yaml` y fusiona sus directivas (usando `awk`) con los secretos base de `.env.example`, generando el archivo final `moodle-matrix-dev/.env`. 
  - **Resolución de Bugs Complejos**:
    - Se resolvió un defecto crítico por el cual la ausencia de un separador manual vaciaba las credenciales inyectadas de base de datos debido a un error de `sed`. 
    - Se solucionó un problema de herencia de contexto (`CWD`) en Windows/WSL forzando explícitamente `docker compose --env-file .env up -d` en el script, asegurando que el demonio de Docker leyera las credenciales exactas.
  - **Control de Flujo Síncrono**: Scripting defensivo (`docker inspect`) haciendo *polling* sobre los Healthchecks de Moodle y Synapse, deteniendo el script hasta reportar estado `healthy`.
  - **Timeouts de Arranque en Frío**: Se aumentó el `start_period` de Moodle en Docker Compose a `180s`, resolviendo falsos positivos de estado `unhealthy` durante las migraciones iniciales masivas de tablas en MariaDB.

### Pruebas Realizadas
- **Test de resiliencia de arranque en frío**: Ejecución repetida de `docker compose down -v && rm .env && ./instalar.sh` validando que las bases de datos vacías puedan construirse de cero sin fallos por timeout.
- **Script Integrado de Verificación de Puertos**: Desarrollo de `moodle-matrix-dev/scripts/test-services.sh` para hacer *curl* contra los puertos 8000, 8008 y 8081 evaluando respuestas de servidor válidas (códigos `200/301/302/400`).

---

## Fase 2: Almacén de Mapeos (FastAPI + SQLite)
Fase dedicada a diseñar e implementar el servicio que persistirá qué repositorio y sala Matrix corresponde a qué alumno. Se descartó inyectar una tabla en la BD de Moodle, apostando por un microservicio totalmente desacoplado.

### Desarrollo e Implementación
- **Microservicio REST (`mapeo-api`)**:
  - Desarrollado en Python puro con **FastAPI** y base de datos local **SQLite** (a través de ORM SQLAlchemy).
  - Modelos ORM: Entidad única con restricciones lógicas (`moodle_user_id`, `moodle_course_id`, `github_fork_url`, `matrix_room_id`). Incluye `UniqueConstraint` para prohibir dos repositorios de un mismo alumno en la misma asignatura.
  - Punteado tecnológico estricto: Todo el código refactorizado a sintaxis moderna compatible con Python 3.14 (SQLAlchemy v2 y Pydantic v2).
- **Endpoint Design**:
  - `POST /mapeos`: Inserta registros (201 Created).
  - `GET /mapeos?moodle_user_id=X&moodle_course_id=Y`: Filtra (200 OK) o deniega si no existe (404 Not Found).
- **Hardening y Seguridad End-to-End**:
  - **Aislamiento de Red**: El puerto 8000 de FastAPI no hace _bind_ con el anfitrión de Docker; solo los demás contenedores pueden alcanzar su URL interna `http://mapeo-api:8000`.
  - **Protección por Token**: Middleware que bloquea accesos sin la cabecera `Authorization: Bearer <TOKEN>`.
  - **Auto-generación Criptográfica**: Si el script detecta en la inicialización que la variable `MAPEO_API_TOKEN` es un placeholder (`changeme`), inyecta en su lugar una cadena hexadecimal segura generada al vuelo con `openssl rand -hex 16`.
  - **Política de Fail-Fast**: Código introducido en la capa de inicialización (`@app.on_event("startup")`) en `app/main.py` que lee las variables de entorno de FastAPI; si `MAPEO_API_TOKEN` está vacía, no definida o contiene `changeme`, lanza de forma deliberada un `RuntimeError`, causando que el contenedor muera inmediatamente y alertando al administrador.

### Pruebas Realizadas
- **Suite de Testing Automatizado (`moodle-matrix-dev/mapeo-api/tests/test_mapeos.py`)**:
  - Se utilizó `pytest` y `TestClient` implementando inyección de dependencias para sobrescribir la sesión de la base de datos de producción con una SQLite in-memory efímera (`sqlite://`).
  - **Prueba 1 (`test_create_and_read_mapeo`)**: Certifica que un payload JSON válido es procesado (`201`), y posteriormente una consulta GET a esa clave devuelve los atributos exactos insertados (sala matrix correcta).
  - **Prueba 2 (`test_read_nonexistent_returns_404`)**: Certifica la intercepción de peticiones en blanco (devolviendo `404 Not Found`).
  - **Prueba 3 (`test_same_user_different_courses`)**: Comprueba que el esquema relacional permite a un usuario de ID `15` tener un repositorio en el curso `1` y otro en el curso `2`. A su vez, garantiza que un intento de sobrescribir el curso `2` sea denegado directamente por el ORM con un `409 Conflict`.
- **Pruebas Manuales de Integración Docker**:
  - Simulaciones `curl` ejecutadas desde dentro de la *shell* de Moodle (`docker exec -it ...`) confirmando el rechazo de credenciales nulas (`401 Unauthorized`) frente al éxito con el Bearer Token válido.

---

## Fase 3: Bloque Moodle `block_bdc` (Base de Datos de Conocimiento)
Esta fase conectó el frontend del LMS (Moodle) con el backend de orquestación, implementando un plugin de Moodle robusto, tolerante a fallos y sin vulnerabilidades de concurrencia.

### Desarrollo e Implementación
- **Arquitectura del Bloque**:
  - Desarrollo de un plugin de bloque estándar (`moodle_plugins/block_bdc`) con su `version.php`, `block_bdc.php` y cadenas de idioma.
  - Se sobreescribió el método `applicable_formats()` devolviendo `array('course-view' => true)` para forzar que Moodle permita su instalación en las páginas principales de los cursos, ya que por defecto los bloques huérfanos de formato solo se muestran en el *Site Home*.
- **Integración Transaccional e Idempotencia (`view.php`)**:
  - Para evitar la creación de salas duplicadas en Matrix si un usuario hace "doble clic" o lanza múltiples peticiones asíncronas, se utilizó la **Locking API** nativa de Moodle (`core\lock\lock_config`).
  - **Fallback de Idempotencia**: Si, por alguna condición de carrera remota o fallo de red local, Moodle lanza la orden de creación pero el microservicio de mapeo devuelve un HTTP `409 Conflict` (porque la sala ya se registró milisegundos antes), el bloque captura la excepción silenciosamente y vuelve a lanzar un `get_mapeo()` para recuperar la sala recién inyectada, asegurando la redirección correcta.
- **Evitación de Conflictos (Doxygen vs Moodle Autoloader)**:
  - **El Problema**: Doxygen fallaba (modo estricto) al encontrar nombres de clases con guión bajo precedidos por namespaces PHP (`\block_bdc\mapeo_client`). Si se retiraban los namespaces pero los ficheros se dejaban en la carpeta `classes/`, el autoloader estricto de Moodle 4+ provocaba un error fatal (`exit 1`) durante el proceso de actualización de la base de datos de Docker.
  - **La Solución**: Los clientes API de mapeo y Synapse fueron movidos estratégicamente a la carpeta `lib/` (usando nombres de clase legacy como `block_bdc_mapeo_client`), puenteando por completo el autoloader automático de Moodle y cargándolos de forma manual vía `require_once`. Esto resolvió limpiamente los conflictos de Doxygen y Moodle de un plumazo.
- **Despliegue Continuo (Docker)**:
  - Se configuró el mapeo de volumen del bloque en el `docker-compose.yml` conectando el código local con `/bitnami/moodle/blocks/bdc`, permitiendo a Moodle detectar y actualizar el código en tiempo real.

### Pruebas Realizadas
- **Suite de Testing PHPUnit (`bdc_creation_test.php`)**:
  - Simulación completa de interacción (Mocks) sustituyendo a los clientes reales por *stubs* configurados.
  - Validaciones de creación de usuarios ficticios a través del `getDataGenerator()` de Moodle.
  - **Test `test_sala_existente`**: Valida que si la sala ya existe, no se invoque nunca el cliente de creación de Synapse.
  - **Test `test_crear_sala_nueva`**: Valida que si la sala no existe, se llame a Synapse, se obtenga un ID y se envíe a la API.
  - **Test `test_idempotencia_409`**: Inyecta una excepción `409 Conflict` artificial en el mock del `mapeo_client` y valida que el bloque sea capaz de procesarlo y finalizar con éxito recuperando la sala original.
- **Test Estricto Doxygen**: `WARN_AS_ERROR=YES` superado con éxito.
- **Validación Manual E2E**: Despliegue de dos usuarios ficticios simultáneos (`alumno1` y `alumno2`) comprobando que se redirigían a dos salas de Matrix completamente distintas y generaban dos registros únicos en la API de mapeos local.

---

## Fase 4: Provisionamiento GitHub y Pruebas de Integración
Esta fase cerró el ciclo de automatización entre Moodle, el microservicio de mapeos y GitHub, permitiendo generar repositorios de curso y de alumno de forma reproducible y segura.

### Desarrollo e Implementación
- **Centralización del Token GitHub**: El PAT se movió a `config/config.yaml` y el script `instalar.sh` genera automáticamente `moodle-matrix-dev/.env` inyectando la variable `GITHUB_PAT` para que el stack y los scripts puedan reutilizarla sin depender de secretos dispersos.
- **Aprovisionamiento Automático desde Moodle**: Se integró en la API Mapeo el endpoint `POST /cursos`. El bloque de Moodle (`block_bdc`) ahora registra un observador de eventos (`\core\event\course_created`) que intercepta la creación de cursos en la plataforma.
  - Al detectar un nuevo curso, Moodle envía una petición HTTP a la API.
  - La API se encarga de aprovisionar dinámicamente en GitHub el repositorio oficial (`<Asignatura>-Oficial`) a partir de la plantilla maestro (`BdC-template`).
  - La API marca el repositorio resultante como `is_template=true`.
  - El resultado de la operación se devuelve de forma síncrona, y Moodle inyecta notificaciones nativas (`success`/`error`) en la interfaz para informar al administrador del LMS en tiempo real.
- **Aprovisionamiento de repositorios de alumno**: Se amplió `moodle-matrix-dev/mapeo-api/app/services/github_service.py` para que, al acceder un alumno a la sala por primera vez, el sistema provisione un fork a partir de la plantilla recién generada.
- **Integración con FastAPI y Settings**: El servicio de GitHub lee la configuración desde `GITHUB_PAT` y desde `app/core/config.py`, facilitando la portabilidad.

### Pruebas Realizadas
- **Suite de pruebas del servicio GitHub**: Se añadió `moodle-matrix-dev/mapeo-api/tests/test_github_service.py` con pruebas que cubren:
  - creación de un repositorio nuevo,
  - reutilización de un repositorio ya existente,
  - manejo de errores controlados de la API,
  - lectura del PAT desde los settings del servicio.
- **Validación de flujo real**: Se ejecutó el script de provisionamiento con un PAT válido y se comprobó que el repositorio oficial se generaba o reutilizaba correctamente, sin detenerse por el caso de propietario-colaborador.
- **Validación documental**: Se verificó que la documentación generada por Doxygen siguiera siendo válida en modo estricto con `WARN_AS_ERROR=YES`.

### Resultado Obtenido
El proyecto ya permite completar el ciclo completo de aprovisionamiento de repositorios en GitHub desde la instalación base, reduciendo la intervención manual y dejando preparada la infraestructura para el siguiente escalado en entornos reales de aula.

### Prueba Manual de Moodle
Para validar el flujo completo desde la interfaz, se puede crear manualmente un usuario de prueba en Moodle con los siguientes datos:
- Nombre de usuario: `student1`
- Contraseña: `Student1!`
- Nombre completo: `Student One`
- Correo electrónico: `student1@example.com`

Una vez creado, se matricula en un curso de prueba y se ejecuta la acción del bloque BDC desde esa cuenta para comprobar que se genera el mapeo y el repositorio asociado.
