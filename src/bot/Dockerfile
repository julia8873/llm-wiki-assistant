FROM dock.mau.dev/maubot/maubot:latest

# Instalar dependencias globales necesarias para el plugin llm-wiki-assistant
RUN apk add --no-cache git build-base python3-dev libffi-dev py3-pip py3-wheel
# Utilizamos --break-system-packages porque Maubot usa un entorno Alpine con Python base
RUN pip install --break-system-packages httpx asyncpg pgvector pypdf rq redis tenacity presidio-analyzer presidio-anonymizer spacy cryptography PyJWT sqlalchemy psycopg2-binary
RUN python -m spacy download es_core_news_lg --break-system-packages
RUN python -m spacy download en_core_web_lg --break-system-packages
