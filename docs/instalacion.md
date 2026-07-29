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
3. Compila y levanta el servidor de documentación Doxygen en modo *detached* (segundo plano).

### Comandos de Operación
| Comando | Acción |
|---|---|
| `./instalar.sh docs serve` | Levanta Doxygen en `http://localhost:8005`. |
| `./instalar.sh docs check` | Verifica consistencia de documentación (`WARN_AS_ERROR=YES`). Falla si hay enlaces rotos. |
| `./instalar.sh up` | Levanta stack Docker Compose (Fase 1). |
| `./instalar.sh down` | Detiene stack conservando volúmenes (Fase 1). |
| `./instalar.sh git setup` | Configura repositorios base (Fase 1). |
| `./instalar.sh bot sync` | Fuerza sincronización base de datos Moodle -> Matrix (Fase 3). |
