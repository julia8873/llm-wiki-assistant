# Instalación y Despliegue

## Instalación Completa con un Solo Comando

```bash
./instalar.sh
```

Ejecuta automáticamente todos los pasos disponibles:

| Paso | Acción | Estado |
| :--: | :--- | :--- |
| 1 | Verificar que Docker está disponible | ✅ Activo |
| 2 | Copiar `.env.example → .env` (si no existe) | ✅ Activo |
| 2 | Copiar `config/config.yaml.example → config/config.yaml` (si no existe) | ✅ Activo |
| 2 | Copiar plantillas `.example` de Maubot (si no existen) | ✅ Activo |
| 3 | Levantar stack Docker (Moodle, Synapse, Element, Maubot…) | ⏳ Fase 1 |
| 4 | Configurar repositorios GitHub | ⏳ Fase 1 |
| 5 | Verificar documentación (`mkdocs build --strict`) | ✅ Activo |

Los pasos marcados como **Fase 1** muestran un aviso claro y continúan.

---

## Otros Comandos Disponibles

Consulta todos los subcomandos con:

```bash
./instalar.sh help
```

### Documentación (Fase 0.1)

```bash
./instalar.sh docs serve   # Levanta MkDocs en http://localhost:8005
./instalar.sh docs check   # Verifica sin warnings (mkdocs build --strict)
```

### Entorno Docker (Fase 1 — Próximamente)

```bash
./instalar.sh up             # Levanta el stack completo
./instalar.sh down           # Para el stack conservando datos
./instalar.sh down --volumes # Para el stack eliminando todos los datos
./instalar.sh logs moodle    # Logs de un servicio específico
./instalar.sh status         # Estado de los contenedores
```

### Configuración GitHub (Fase 1 — Próximamente)

```bash
./instalar.sh git setup
```

### Sincronización del Bot (Fase 3 — Próximamente)

```bash
./instalar.sh bot sync
```
