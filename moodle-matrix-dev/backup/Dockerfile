FROM alpine:3.19

RUN apk add --no-cache postgresql16-client redis tar gzip bash

WORKDIR /scripts

# Configurar crontab para que ejecute el backup a las 03:00 am todos los días
RUN echo "0 3 * * * /scripts/backup.sh > /proc/1/fd/1 2>/proc/1/fd/2" > /etc/crontabs/root

# El comando por defecto ejecutará cron en foreground
CMD ["crond", "-f", "-l", "2"]
