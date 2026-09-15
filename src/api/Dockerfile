FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /code/app

COPY ./alembic.ini /code/
COPY ./alembic /code/alembic

# Variables de entorno por defecto
ENV MAPEO_API_TOKEN="default_token"

EXPOSE 8000

# Añadimos curl para el healthcheck de docker-compose
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
