# Consideraciones Futuras

Este documento recopila las decisiones tecnológicas aplazadas, infraestructuras pendientes de confirmación y futuras fases del desarrollo del sistema.

## Fase 9.2: Backups Locales vs Remotos
- En la Fase 9.2 se implementó un sistema automatizado de copias de seguridad (PostgreSQL y Redis AOF) almacenado localmente mediante un *bind mount* hacia el disco del servidor host.
- **Pregunta Pendiente a IT/UGR**: Existe el riesgo inherente de mantener los backups únicamente en el mismo servidor físico local donde residen los datos de producción. ¿Existe algún sistema de almacenamiento remoto, servidor NFS institucional, o bucket S3 provisto por la UGR al que debamos subir o sincronizar los backups generados de forma automática?
## Infraestructura Git Autoalojada (OSL UGR)
- Se ha confirmado que la Universidad de Granada (UGR) desplegará una instancia de Git autoalojado gestionada por la Oficina de Software Libre (OSL).
- Esta instancia reemplazará (o convivirá con) GitHub/GitLab como proveedor principal del sistema.
- El módulo `self_hosted_provider.py` (desarrollado como un *stub* en la Fase 4.2) **dejará de ser especulativo** y deberá ser implementado en cuanto se provean las credenciales y el acceso a dicha infraestructura.

## Fase 9.3: Rate Limiting y Sincronización Masiva
- En la Fase 9.3 se añadió el control de Rate Limiting para las operaciones masivas de creación y sincronización (tanto en la API HTTP como en los comandos `git push`/`git fetch` del worker).
- **Pregunta Pendiente a IT/UGR**: Si el volumen real de alumnos/cursos concurrentes de la UGR es alto (creación masiva de repositorios al inicio de curso o sincronizaciones simultáneas muy pesadas), es posible que se dispare frecuentemente el límite secundario (Abuse Detection). ¿Conviene solicitar un PAT de organización de GitHub con límite ampliado, o coordinar con IT/UGR el volumen esperado de escritura simultánea para dimensionar esto con datos reales en vez de una estimación?
