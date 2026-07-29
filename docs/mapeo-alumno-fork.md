# Tabla de Mapeo Moodle-Matrix-GitHub

## Justificación Arquitectónica
Moodle 4.2+ incluye nativamente `communication/provider/matrix`, el cual asocia **una única sala compartida por curso**. Este modelo es incompatible con el requerimiento de salas privadas 1:1 por alumno. 
Por ello, se ha implementado el bloque `block_bdc` operando de forma totalmente aislada, comunicándose con un microservicio independiente (`mapeo-api`) que almacena una tabla de mapeo propia.

### Independencia del Subsistema Nativo
El bloque `block_bdc` genera su propia sala privada para el alumno. Se recomienda encarecidamente **desactivar** el subsistema nativo de Comunicación de Matrix en los cursos para evitar confusión cognitiva (el alumno no debe ver dos enlaces de chat distintos).

## Microservicio `mapeo-api`
En la Fase 2, se abstrajo el almacén de mapeos a un microservicio FastAPI + SQLite, asegurando el aislamiento arquitectónico. 

El modelo ORM subyacente maneja la triada relacional:
- `moodle_user_id` (Integer, Unique con course_id)
- `moodle_course_id` (Integer)
- `github_fork_url` (String)
- `matrix_room_id` (String)

## Flujo de Creación (block_bdc)
El siguiente diagrama detalla la arquitectura de idempotencia implementada en `block_bdc/view.php` para evitar salas duplicadas al hacer doble-clic:

```mermaid
sequenceDiagram
    actor Alumno
    participant Moodle as block_bdc (view.php)
    participant Lock as Lock Factory (Moodle)
    participant MapeoAPI as mapeo-api (FastAPI)
    participant Synapse as Synapse Admin API

    Alumno->>Moodle: Clic en "Mi asistente BdC"
    Moodle->>MapeoAPI: GET /mapeos?userid=...&courseid=...
    
    alt Existe mapeo
        MapeoAPI-->>Moodle: matrix_room_id
        Moodle-->>Alumno: 302 Redirect a Element Web
    else No existe mapeo
        Moodle->>Lock: Adquirir candado 'crear_sala_U_C'
        Note over Moodle, Lock: Capa 1: Idempotencia en PHP
        Lock-->>Moodle: Candado Adquirido
        
        Moodle->>MapeoAPI: Doble Check GET /mapeos
        MapeoAPI-->>Moodle: No existe
        
        Moodle->>Synapse: POST /_matrix/client/v3/createRoom
        Synapse-->>Moodle: 200 OK (matrix_room_id)
        
        Moodle->>MapeoAPI: POST /mapeos
        
        alt Éxito
            MapeoAPI-->>Moodle: 201 Created
        else Fallo concurrente (Capa 2)
            MapeoAPI-->>Moodle: 409 Conflict (UniqueConstraint)
            Moodle->>MapeoAPI: GET /mapeos (Recuperar sala real)
            MapeoAPI-->>Moodle: matrix_room_id
        end
        
        Moodle->>Lock: Liberar Candado
        Moodle-->>Alumno: 302 Redirect a Element Web
    end
```
