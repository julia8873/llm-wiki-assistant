# Consideraciones Futuras

Este documento recopila las decisiones tecnológicas aplazadas, infraestructuras pendientes de confirmación y futuras fases del desarrollo del sistema.

## Fase 9.2: Backups Locales vs Remotos
- En la Fase 9.2 se implementó un sistema automatizado de copias de seguridad (PostgreSQL y Redis AOF) almacenado localmente mediante un *bind mount* hacia el disco del servidor host.
- **Pregunta Pendiente a IT/UGR**: Existe el riesgo inherente de mantener los backups únicamente en el mismo servidor físico local donde residen los datos de producción. ¿Existe algún sistema de almacenamiento remoto, servidor NFS institucional, o bucket S3 provisto por la UGR al que debamos subir o sincronizar los backups generados de forma automática?
## Infraestructura Git Autoalojada (OSL UGR)
- Se ha confirmado que la Universidad de Granada (UGR) desplegará una instancia de Git autoalojado gestionada por la Oficina de Software Libre (OSL).
- Esta instancia reemplazará (o convivirá con) GitHub/GitLab como proveedor principal del sistema.
- El módulo `self_hosted_provider.py` (desarrollado como un *stub* en la Fase 4.2) **dejará de ser especulativo** y deberá ser implementado en cuanto se provean las credenciales y el acceso a dicha infraestructura.
