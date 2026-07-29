# Tabla de Mapeo: Alumno - Fork - Sala Matrix

La pieza central del diseño es la tabla de base de datos **`mdl_block_bdc_mapping`**, gestionada por el plugin Moodle `block_bdc`.

## Esquema SQL

```sql
CREATE TABLE mdl_block_bdc_mapping (
    id BIGINT(10) NOT NULL AUTO_INCREMENT,
    userid BIGINT(10) NOT NULL,
    courseid BIGINT(10) NOT NULL,
    github_fork_url VARCHAR(255) NOT NULL,
    github_branch VARCHAR(50) DEFAULT 'main',
    matrix_room_id VARCHAR(255) NOT NULL,
    matrix_room_alias VARCHAR(255) NULL,
    timecreated BIGINT(10) NOT NULL,
    timemodified BIGINT(10) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_course (userid, courseid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Relación con el Subsistema Nativo de Moodle

Moodle (4.2+) incluye `communication/provider/matrix` que crea 1 sala compartida por curso. El plugin `block_bdc` es **completamente independiente** de ese subsistema y no lo intercepta, gestionando sus propias salas privadas 1:1 por alumno.
