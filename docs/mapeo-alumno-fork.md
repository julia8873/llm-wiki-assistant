# Tabla de Mapeo Moodle-Matrix-GitHub

## Justificación Arquitectónica
Moodle 4.2+ incluye nativamente `communication/provider/matrix`, el cual asocia **una única sala compartida por curso**. Este modelo es incompatible con el requerimiento de salas privadas 1:1 por alumno. 
Por ello, se implementa el plugin `block_bdc` operando de forma totalmente aislada con una tabla de mapeo propia.

## Esquema `mdl_block_bdc_mapping`
Gestiona la triada relacional Alumno-Repositorio-Sala.

```sql
CREATE TABLE mdl_block_bdc_mapping (
    id BIGINT(10) NOT NULL AUTO_INCREMENT PRIMARY KEY,
    userid BIGINT(10) NOT NULL,
    courseid BIGINT(10) NOT NULL,
    github_fork_url VARCHAR(255) NOT NULL,
    github_branch VARCHAR(50) DEFAULT 'main',
    matrix_room_id VARCHAR(255) NOT NULL,
    matrix_room_alias VARCHAR(255) NULL,
    timecreated BIGINT(10) NOT NULL,
    timemodified BIGINT(10) NOT NULL,
    UNIQUE KEY uk_user_course (userid, courseid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
