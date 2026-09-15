FROM bitnamilegacy/moodle:latest

# Creamos un enlace simbólico para el plugin.
# Esto evita el error "Device or resource busy" durante la inicialización
# de Bitnami (cuando mueve /opt/bitnami/moodle a /bitnami/moodle), ya que
# mueve el enlace y no el punto de montaje real.
RUN ln -s /moodle-custom-plugin /opt/bitnami/moodle/blocks/bdc
