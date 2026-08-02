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

### Fase 4.1: Integración Completa de Identidad (SSO Delegado Moodle-Matrix) y Limpieza para Producción
- **Aprovisionamiento Automático en Synapse (Sin Mocks)**: Cuando el bloque `bdc` intenta vincular a un usuario a su sala, llama a la API de administración de Synapse (`ensure_user_exists`) para crear la cuenta de Element en segundo plano con una clave aleatoria, impidiendo fallos de invitación. Se configuró un `MATRIX_ACCESS_TOKEN` real de administrador, eliminando los *mocks* temporales y validando la creación real de salas y usuarios.
- **Nombres Dinámicos de Salas**: Moodle ahora inyecta dinámicamente el nombre de la asignatura y enlaza el "topic" (descripción) de la sala al repositorio aprovisionado, logrando que el estudiante vea explícitamente "Asistente IA - <Nombre de la Asignatura>".
- **Autenticación Delegada (Password Provider)**: Se instaló el módulo `matrix-synapse-rest-password-provider` en el contenedor de Synapse para que las comprobaciones de contraseñas se deleguen a Moodle. Se parcheó para inyectar la cabecera `Host` correcta (`localhost:8000`) hacia Moodle, esquivando los bloqueos por protección de URL (`$CFG->wwwroot`).
- **Endpoint de Autenticación de Moodle (`api/auth.php`)**: Se refactorizó este script para utilizar directamente los plugins nativos de autenticación (`get_auth_plugin()->user_login()`) en lugar de funciones de alto nivel. Esto previno excepciones fatales por redirección de sesión oculta (`redirecterrordetected`), consiguiendo una respuesta cruda (JSON) limpia.
- **Fricción Cero en Producción (Desactivación E2EE)**: Se desactivaron en `element-config.json` los avisos intrusivos de cifrado de extremo a extremo (E2EE) y de respaldo de llaves cruzadas (`UIFeature.keyBackup` y `UIFeature.crossSigning`), ya que para interacciones 1:1 con un LLM académico la usabilidad prioriza sobre el cifrado dispositivo-a-dispositivo.

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

---

## Fase 4.2: Abstracción de Proveedores Git (GitHub, GitLab, OSL)
Esta sub-fase permitió independizar el sistema del proveedor único GitHub, introduciendo una capa de abstracción para soportar múltiples plataformas Git (como GitLab o servicios autoalojados de la universidad) y preparando la base de datos para entornos de producción.

### Desarrollo e Implementación
- **Interfaz `GitProviderClient`**: Se refactorizó el servicio de aprovisionamiento (`github_service.py` pasó a estar gobernado por el `GitProviderFactory`) para que el sistema pueda inyectar dinámicamente la implementación correspondiente según la configuración.
- **Implementación de GitLab**:
  - Debido a que la API de exportación/importación de GitLab es asíncrona, se optó por una estrategia síncrona ("Fork + Delete"). El sistema clona el repositorio oficial mediante un fork y automáticamente rompe el vínculo (`DELETE /projects/:id/fork`), emulando perfectamente la funcionalidad de "Use this template" de GitHub sin latencias de espera.
- **Preparación para Proveedor Autoalojado (OSL)**:
  - Se estructuró un `self_hosted_provider.py` que actualmente lanza un error documentado indicando cómo configurarlo una vez se determine la plataforma exacta (ej. Gitea/Forgejo mediante endpoint `/generate` o GitLab CE/EE reutilizando el cliente de GitLab).
- **Migraciones con Alembic (mapeo-api)**:
  - Se introdujo Alembic para gestionar de forma profesional las migraciones de la base de datos (SQLite) del microservicio de mapeos, reemplazando la creación estática inicial y preparando el terreno para escalar el esquema en producción.

### Pruebas Realizadas
- **Pruebas de Factory**: Validaciones unitarias sobre la inyección de dependencias (`test_git_provider_factory.py`) para confirmar que el sistema instancie correctamente el proveedor definido en la configuración sin romper la lógica existente.
- **Migración Baseline**: Borrado y recreación de la base de datos efímera aplicando Alembic exitosamente, garantizando un flujo CI/CD sin fricciones.

---

## Fase 5: Plugin Maubot (Asistente LLM) e Ingesta OKF v0.1
Esta fase representa el núcleo de la Inteligencia Artificial del proyecto. Se desarrolló el plugin nativo para Maubot capaz de gestionar conversaciones en salas de Matrix, ingerir documentos y orquestar comandos interactivos aplicando el estándar OKF v0.1.

### Desarrollo e Implementación
- **Motor Multi-LLM (`llm_clients.py`)**:
  - Interfaz abstracta para soportar proveedores compatibles con OpenAI y de forma nativa la API de Google Gemini (Multimodal).
  - Configuración dinámica de parámetros (temperatura, max_tokens) heredados desde `config.yaml`.
  - Soporte explícito para inferencia multimodal (OCR Visual) mediante la subida de binarios (`inlineData`) para interpretar esquemas o apuntes a mano utilizando `gemini-1.5-flash-latest`.
- **Pipeline de Ingesta Inteligente (`repo_reader.py`)**:
  - **Detección de Archivos**: Cuando el alumno envía un fichero por el chat de Matrix (ej. un PDF), el bot entra en modo interactivo, preguntando si desea extracción normal (PyPDF) o extracción visual (OCR Inteligente).
  - **Estándar OKF v0.1**: El bot clona el repositorio del alumno, lee dinámicamente el documento `AGENTS.md` maestro, e inyecta estas reglas en el _system prompt_ del LLM.
  - **Anti-Fragilidad en Parseo**: Se abandonó la generación de salida en formato JSON en favor de etiquetas XML puras (`<file path="...">...</file>`). Esto resolvió errores críticos de parseo (Unterminated String) que ocurrían cuando el LLM olvidaba escapar comillas al generar contenido Markdown masivo.
  - El sistema crea dinámicamente la estructura del repositorio:
    - `raw/`: Archivo original.
    - `recursos/`: Resumen fuente del documento (`type: Source`).
    - `conceptos/`: Ficheros aislados de teoría (`type: Concept`).
    - `entidades/`: Menciones a personas, herramientas o productos (`type: Entity`).


  - **Inyección YAML**: Todos los archivos generados incluyen forzosamente su cabecera YAML Frontmatter exigida por el estándar OKF.
  - **Git Automation**: El bot hace un `git add .`, commit y push directo de los resultados de vuelta al fork de GitHub del estudiante, todo en segundo plano.
- **Comandos de Chat Interactivos (`assistant.py`)**:
  - Detección de comandos de usuario mediante intercepción estricta en el `handle_message`.
  - **`!ayuda` / `!comandos`**: Menú dinámico de asistencia.
  - **`!deshacer` / `!revertir`**: Comando de alta prioridad para corregir extracciones erróneas. El bot lee el historial de Git; si el último commit fue una ingesta automática, invoca un `git revert HEAD --no-commit`, identifica los ficheros borrados, documenta explícitamente los nombres de dichos ficheros en `bitacora/log.md`, realiza commit de la reversión y finalmente re-indexa la base vectorial (RAG) para borrar de su memoria cualquier rastro de los conceptos.
- **Auditoría y Documentación**:
  - Aplicación de docstrings estilo Doxygen (`@brief`, `@param`) a todos los métodos expuestos (`ingest_file_okf`, `revert_last_ingest`, `get_response`, `handle_message`).
  - Validación superada con `./instalar.sh docs check` garantizando cero advertencias arquitectónicas.

### Pruebas Realizadas
- **Prueba Multimodal OCR**: Se comprobó que el flujo detecta respuestas `ocr`, deriva el binario hacia Gemini y extrae texto no parseable por PyPDF.
- **Stress-Test de Longitud (Tokens)**: Se forzó el parámetro `max_tokens_override=8192` asegurando que resúmenes extremadamente grandes no sean truncados por el proveedor.
- **Prueba de Reversión Ciega (`!deshacer`)**: Se comprobó la integridad del repositorio al hacer `!deshacer`. Git manejó limpiamente el borrado de la carpeta `entidades/` (creada dinámicamente gracias al uso de `git add .`) y la bitácora (`log.md`) reflejó limpiamente los archivos revertidos sin romper el historial del estudiante.

---

## Fase 5.1: Sincronización Ascendente (Upstream Sync)
Esta sub-fase se implementó para resolver el flujo de actualización bidireccional, permitiendo a los profesores propagar cambios en el material oficial (`material-oficial/` en la plantilla de asignatura) a todos los repositorios generados por los estudiantes, sin colisionar con el trabajo de estos y solucionando las limitaciones de la API *generate from template* de GitHub.

### Desarrollo e Implementación
- **Cola de Tareas Asíncronas (Redis + RQ)**:
  - Se introdujo un servicio `redis` y un worker dedicado (`sync-worker`) en `docker-compose.yml` para desacoplar el procesamiento pesado de Git del bloque de ejecución de `mapeo-api` y `maubot`.
  - El worker utiliza la misma base de código que `maubot` compartiendo volumen, lo que permite la reutilización de lógica (`git_utils.py`).
- **Endpoint Webhook (`mapeo-api`)**:
  - Nuevo endpoint `POST /sync/oficial-updated` protegido con HMAC (`X-Hub-Signature-256`) utilizando un secreto configurado globalmente (`GITHUB_WEBHOOK_SECRET`).
  - Al recibir un evento `push` en la rama principal, busca todos los repositorios de alumnos asociados al repositorio oficial mediante el campo `official_repo_url` (ahora persistido en base de datos) y encola un trabajo en RQ por cada uno.
- **Motor de Git Centralizado (`git_utils.py`)**:
  - Lógica para asegurar el clonado, la inyección dinámica de credenciales OAuth (para GitHub HTTPS con PAT) y, críticamente, la asignación del remoto `upstream` apuntando al repositorio del profesor.
- **Flujo de Sincronización Total (Git Archive)**:
  - Se sustituyó el *checkout selectivo* por un `git archive upstream/main | tar -x --exclude='logs' --exclude='logs/*' --exclude='bitacora' --exclude='bitacora/*' --exclude='profesores/*/logs' --exclude='profesores/*/logs/*' --exclude='profesores/*/bitacora' --exclude='profesores/*/bitacora/*' --exclude='profesores/*/okf/log.md' -C material-oficial/`. Esto garantiza que la carpeta `material-oficial/` siempre contenga una réplica fiel de la estructura didáctica del profesor, excluyendo inteligentemente tanto las carpetas raíz de `logs`/`bitacora` del repositorio base como las carpetas privadas de cada docente, previniendo sobreescrituras en el repositorio del estudiante.
  - Tras extraer los ficheros, el bot adjunta automáticamente una entrada de registro al archivo `logs/log.txt` de la raíz del alumno, realiza un commit (firmando incondicionalmente como `LLM Wiki Assistant`) y un push al `origin` del estudiante.
- **Integración con Maubot**:
  - Notificación activa a través de un HTTP POST directamente a la API de Synapse (`/_matrix/client/v3/rooms/{room_id}/send/m.room.message`) informando al estudiante que su material oficial ha sido actualizado automáticamente.
  - Implementación del comando manual `!sincronizar` / `!sync` en `assistant.py` para forzar la actualización a demanda.
- **Reorganización Estructural**:
  - Búsqueda de las reglas del bot reorientada desde `/AGENTS.md` local a `material-oficial/AGENTS.md`.
- **Corrección de Problemas de Hot-Reload en Python**:
  - Se previno un error crítico (`ZipImportError: bad local file header`) que ocurría si el plugin `.mbp` era reconstruido mientras el contenedor Maubot estaba levantado. La solución consistió en promover la importación del módulo de tareas de sincronización (`_async_sync_repo_task`) a la cabecera del archivo `assistant.py`, evitando así importaciones diferidas (*lazy imports*) que accedieran a índices de archivo ZIP cacheados y obsoletos.

### Pruebas Realizadas
- **Idempotencia de Git**: Ejecución repetida de clonado sin borrar la carpeta `/tmp/llm_wiki_repos` para certificar la actualización segura (`fetch`/`reset`).
- **Validación del Enrutamiento Worker-Redis**: Verificación en logs comprobando el inicio correcto del proceso de RQ Worker con acceso a las variables globales.
- **Compilación Doxygen**: Se superó el filtro `WARN_AS_ERROR=YES` actualizando los docstrings de los nuevos métodos (`asegurar_repo_local`, `sync_repo_task`).

## Fase 6: Registro de Interacciones y Distributed Locking

### Resumen de la Fase
Se implementó el encolado asíncrono para registrar el flujo completo RAG de interacciones (Mensaje -> Contexto -> Respuesta del LLM) hacia los repositorios de cada alumno, de forma no bloqueante para las respuestas en vivo de las salas de Matrix. Además, para proteger el árbol local de Git frente a colisiones (e.g. un sync asíncrono de un profesor interrumpiendo la escritura de logs asíncronos), se implementó un sistema estricto de cerrojo distribuido nativo.

### Cambios Técnicos
- **Distributed Locking con Redis Async**: Uso estricto de `redis.asyncio` como cerrojo (`distributed_repo_lock`) cubriendo el scope entero de las tareas de Git en el `sync-worker` (desde la preparación local hasta el `git push` final).
  - **TTL y Heartbeat**: TTL ajustado a **60 segundos** en base a medidas reales sobre latencias de red en `git clone`/`push`. Se instauró una tarea secundaria que hace *heartbeat* (renueva el TTL) cada 20s para prevenir interrupciones prematuras.
  - **Serialización en Espera (Inline Blocking)**: El `blocking_timeout` se ha ampliado a 30s. Ante concurrencia sobre el mismo repositorio, los procesos esperan de forma dócil y se encolan secuencialmente. Si el lock excede ese límite, se relega a reintentos pasivos de RQ.
- **Idempotencia de Logs**: Los fallos puntuales de `git push` lanzarán un reintento del Job. El código valida el hash del nuevo log JSON contra el fichero existente en disco previniendo duplicidades e ignorando selectivamente el commit si ya había transitado localmente.
- **Doble Orquestación**: Se segregó el escalado del worker (`sync-worker-1` y `sync-worker-2` independientes) en `docker-compose.yml` sorteando la limitación sintáctica de `deploy.replicas` en entornos no-Swarm.
- **Tolerancia a fallos en UI**: El encolado de interacciones implementa un fallback (`try/except`) para que, ante saturación del broker Redis, la experiencia del usuario (respuestas por chat) permanezca intacta (degradación grácil).

## Fase 7: Consolidación de Tests y Corrección de Regresiones

### Resumen de la Fase
El objetivo principal de esta fase fue unificar las distintas suites de pruebas de los subsistemas (API, Plugin Moodle, Bot/Worker y Documentación) bajo un único orquestador automatizado y resolver las regresiones detectadas en el refactor de proveedores Git de la Fase 4.2.

### Cambios Técnicos
- **Orquestador de Pruebas (`instalar.sh --test`)**:
  - Se introdujo el flag `--test` en `instalar.sh` (con opción `--full` para forzar la recreación desde cero del entorno Docker y borrado de variables).
  - El script orquesta la ejecución en **5 bloques independientes**, evitando que un fallo temprano (ej. en Moodle) detenga la ejecución del resto de las pruebas. Al finalizar, vuelca una tabla resumen con los resultados de:
    - **Bloque A (Infraestructura)**: Test de puertos y servicios con `test-services.sh`.
    - **Bloque B (API Mapeo)**: Migraciones Alembic automáticas y suite de `pytest`. Se adaptaron rutas y configuraciones para que `pytest` se ejecute mapeando directorios internos del contenedor.
    - **Bloque C (Moodle)**: Detección inteligente del estado de `PHPUnit`. Si el entorno no está inicializado, el script lanza silenciosamente `composer install`, el *build* e *init* de PHPUnit antes de ejecutar las pruebas del plugin `block_bdc`.
    - **Bloque D (Bot / Worker)**: Pruebas unitarias de Maubot usando `pytest` internamente en el contenedor worker.
    - **Bloque E (Documentación)**: Validación estricta con Doxygen (`cmd_docs check`).
- **Resolución de Regresiones en Pruebas**:
  - Se detectó y resolvió una regresión importante originada en la Fase 4.2, donde los tests originales de creación de repositorio en GitHub se eliminaron por error.
  - Se restauró la cobertura completa rescribiendo `test_github_provider.py`, adaptado ahora a interactuar con la abstracción `GitHubProvider` invocada por el Factory.
  - Cobertura validada: creación de repositorios exitosa, reutilización de repositorios existentes, manejo asertivo de respuestas fallidas (HTTP 500) y parseo correcto de la variable `GITHUB_PAT` tanto por el entorno como por el fichero `.env`.
- **Exclusiones Conscientes**:
  - Scripts interactivos o sin código de salida fiable (como `test_race.py`) y comprobaciones que fuerzan reinicios abruptos (`hot-reload`) se mantienen exclusivamente para comprobaciones manuales, garantizando la fiabilidad de CI/CD para el resto del sistema.
  - La idempotencia profunda (e.g. clonado resiliente de GitLab) queda registrada y documentada como deuda técnica menor.

---

## Fase 8: Actualización y Reestructuración de Documentación

### Resumen de la Fase
Se llevó a cabo una revisión integral y actualización de la documentación técnica para alinearla con los desarrollos recientes de las Fases 5.1, 6 y 7. El objetivo fue consolidar las explicaciones arquitectónicas, de seguridad y los flujos de integración.

### Cambios Técnicos
- **Reestructuración de Nomenclatura**: Se renombró el documento `mapeo-alumno-template.md` a `mapeo-alumno-repositorio.md` para reflejar con mayor precisión el modelo actual de "Alumno-Repositorio-Sala", detallando la justificación de usar "Generate from Template" en lugar de "Fork".
- **Actualización de Arquitectura e Interfaces**: Se actualizaron `README.md`, `arquitectura.md` y `bot.md` para incorporar los nuevos flujos asíncronos, la orquestación de colas, y la infraestructura de workers.
- **Documentación de API y Seguridad**:
  - `api-mapeo.md` actualizado para detallar las nuevas estructuras y parámetros.
  - `seguridad.md` ampliado para detallar el manejo de tokens dinámicos por proveedor Git (`GITHUB_PAT`, `GITLAB_TOKEN`, `GIT_SELF_HOSTED_TOKEN`), claves de LLMs (`OPENAI_API_KEY`, `GEMINI_API_KEY`) y los secretos entre subsistemas (como `GITHUB_WEBHOOK_SECRET` para proteger la cola asíncrona mediante HMAC).

---

## Fase 9.1: Hardening de Producción (Migración a PostgreSQL)
Esta fase inició el proceso de estabilización del entorno para cargas concurrentes reales de producción, abordando específicamente el cuello de botella de escritura concurrente en la API central (anteriormente en SQLite).

### Desarrollo e Implementación
- **Motor de Base de Datos Obligatorio**: Se introdujo PostgreSQL (`postgres:16-alpine`) en `docker-compose.yml` como la base de datos exclusiva para producción en `mapeo-api`.
- **Fail-Fast en Orquestador**: Se dotó a `instalar.sh` de los flags `--env=production` y `--env=dev`. El modo de producción valida estrictamente la existencia de una variable `DATABASE_URL` válida; de no encontrarla, detiene el arranque de forma preventiva para evitar arrancar con SQLite en entornos sensibles.
- **Parametrización Híbrida Segura (`db.py`)**: Se abstrajo la lógica de conexión para que los parámetros inseguros (`check_same_thread=False`) se apliquen exclusivamente cuando se detecta el dialecto `sqlite` (usado solo bajo `--env=dev`), protegiendo la conexión PostgreSQL.

### Pruebas Realizadas
- **Validación de Migraciones (Alembic)**: Se validó que el esquema generado (Fase 4.2) es verdaderamente agnóstico. Se comprobó la ejecución `alembic upgrade head` contra una base de datos PostgreSQL en blanco, generando las tablas sin conflictos.
- **Prueba de Carga / Concurrencia Simultánea**:
  - Se desarrolló `test_concurrencia.py` para inyectar 60 peticiones `POST /mapeos/` simultáneas.
  - Al ejecutarlo sobre SQLite, el motor colapsó según lo esperado devolviendo errores HTTP 500 (`database is locked`).
  - Al ejecutarlo sobre PostgreSQL, completó el 100% de las escrituras de forma atómica sin ningún error de concurrencia.

---

## Fase 9.2: Hardening de Producción (Backup Automatizado)
Esta fase abordó el riesgo crítico de pérdida de datos en producción introduciendo un sistema de copias de seguridad automatizado y validando exhaustivamente el proceso de recuperación ante desastres.

### Desarrollo e Implementación
- **Automatización de Backups (`backup.sh` y Cron)**: Se introdujo un nuevo contenedor de `backup` (Alpine Linux con `crond`, `postgresql16-client` y `redis`) que ejecuta un script diariamente a las 03:00 am.
- **Estrategia Dual de Respaldo**:
  - PostgreSQL: Dumps generados mediante `pg_dump -Fc`.
  - Redis: En lugar de usar instantáneas RDB, el script empaqueta (con `tar`) de forma segura el directorio real `appendonlydir` montado en solo lectura, lo que garantiza 0 pérdida de trabajos encolados y preserva el diseño de durabilidad AOF de la Fase 6.
- **Política de Retención Local**: El script limpia automáticamente backups antiguos reteniendo los últimos 7 días y un backup semanal de las últimas 4 semanas.
- **Seguridad y Aislamiento**: Los respaldos se generan de forma no intrusiva mediante *bind mounts* en el host físico (`/backups`) y el contenedor de backup interactúa con los volúmenes de producción solo en modo `ro` (read-only).

### Pruebas Realizadas
- **Prueba de Recuperación ante Desastres (Disaster Recovery Test)**:
  - Se pobló de datos reales una instancia en producción (datos en PostgreSQL y trabajos RQ en Redis AOF).
  - Se eliminaron por completo y deliberadamente los volúmenes `postgres_api_data` y `redis_data` simulando un fallo catastrófico.
  - Se restauró PostgreSQL (`pg_restore -c`) y el directorio `appendonlydir` de Redis desde el último `tar.gz` generado por el cron.
  - La verificación posterior demostró la integridad total de los datos restaurados.

---

## Fase 9.3: Hardening de Producción (Rate Limiting y Sincronización Masiva)
Esta fase incorporó resiliencia frente a cuellos de botella en la comunicación con APIs externas (GitHub/GitLab) al procesar creaciones masivas o sincronizaciones simultáneas de muchos alumnos.

### Desarrollo e Implementación
- **Detección Precisa en `mapeo-api` (HTTP)**: Se unificó la captura de errores 403/429 en `github_provider.py` y `gitlab_provider.py`. Usando las cabeceras HTTP reales (`Retry-After` o `X-RateLimit-Reset`), la API puede propagar el tiempo exacto de espera de la plataforma.
- **Detección de Mejor Esfuerzo en Sync Worker (Git CLI)**: Debido a que las operaciones HTTPS nativas de `git` descartan las cabeceras HTTP, se implementó en `tasks.py` y `git_utils.py` una detección basada en el `stderr` del comando binario. Ante bloqueos secundarios (ej. *abuse detection*), se usa un esquema de backoff exponencial conservador, complementado por comprobaciones oportunistas al endpoint `/rate_limit` de GitHub.
- **Reencolado Dinámico**: La captura de `GitHubRateLimitError` dentro del worker invoca dinámicamente a `enqueue_in` de RQ, reencolando las tareas fallidas (creación de repositorios del profesor, sincronización de alumnos, logging de interacciones) para que se retomen automáticamente una vez el bloqueo se haya mitigado, sin que se pierdan jobs.

### Pruebas Realizadas
- **Tests Automatizados de Backoff**: Se añadieron suites de prueba mockeadas (`test_rate_limiting.py`) para verificar que el reencolado respeta los incrementos exponenciales y procesa correctamente los *timestamps* de limitación primaria cuando están disponibles.
