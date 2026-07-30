FROM dock.mau.dev/maubot/maubot:latest

# Instalar dependencias globales necesarias para el plugin llm-wiki-assistant
RUN apk add --no-cache git
# Utilizamos --break-system-packages porque Maubot usa un entorno Alpine con Python base
RUN pip install --break-system-packages httpx asyncpg pgvector
