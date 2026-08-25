import asyncpg
import logging
from typing import List, Dict, Any, Tuple
from pgvector.asyncpg import register_vector

logger = logging.getLogger("llm_wiki.vector_store")

class VectorStore:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(self.dsn)
                async with self.pool.acquire() as conn:
                    # Habilitar extensión pgvector
                    await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
                    await register_vector(conn)
                    
                    # Crear tabla de chunks. Utilizamos un embedding_size generoso o sin especificar
                    # para permitir diferentes modelos (OpenAI 1536, Gemini 768, etc.)
                    # En pgvector, si no especificamos tamaño, acepta cualquier vector.
                    await conn.execute('''
                        CREATE TABLE IF NOT EXISTS document_chunks (
                            id SERIAL PRIMARY KEY,
                            repo_id TEXT NOT NULL,
                            file_path TEXT NOT NULL,
                            content TEXT NOT NULL,
                            embedding vector
                        );
                        
                        -- Crear índice para mejorar búsqueda por repo_id
                        CREATE INDEX IF NOT EXISTS idx_repo_id ON document_chunks(repo_id);
                    ''')
            except Exception as e:
                logger.error(f"Error conectando a pgvector: {e}")
                raise

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def clear_repo(self, repo_id: str):
        """Elimina todos los chunks de un repositorio específico antes de reindexar."""
        if not self.pool:
            await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM document_chunks WHERE repo_id = $1", repo_id)

    async def add_chunks(self, repo_id: str, chunks: List[Dict[str, Any]]):
        """Añade chunks con sus embeddings a la base de datos."""
        if not self.pool:
            await self.connect()
            
        if not chunks:
            return
            
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            # Preparar datos para executemany
            data = [(repo_id, c["file_path"], c["content"], c["embedding"]) for c in chunks]
            
            await conn.executemany(
                "INSERT INTO document_chunks (repo_id, file_path, content, embedding) VALUES ($1, $2, $3, $4)",
                data
            )

    async def search(self, repo_id: str, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Busca los chunks más similares usando distancia L2 o coseno."""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            # Usamos operador <=> (Cosine distance) soportado por pgvector
            # FILTRADO ESTRICTO POR REPO_ID: GARANTIZA AISLAMIENTO ENTRE SALAS
            rows = await conn.fetch('''
                SELECT file_path, content 
                FROM document_chunks 
                WHERE repo_id = $1 
                ORDER BY embedding <=> $2 
                LIMIT $3
            ''', repo_id, query_embedding, limit)
            
            chunks = [{"file_path": r["file_path"], "content": r["content"]} for r in rows]
            return chunks

    async def get_all_files(self, repo_id: str) -> List[str]:
        """Obtiene la lista de todos los archivos indexados para un repositorio."""
        if not self.pool:
            return []
            
        async with self.pool.acquire() as conn:
            try:
                records = await conn.fetch('''
                    SELECT DISTINCT file_path 
                    FROM document_chunks 
                    WHERE repo_id = $1 
                    ORDER BY file_path
                ''', repo_id)
                return [r['file_path'] for r in records]
            except Exception as e:
                logger.error(f"Error obteniendo archivos: {e}")
                return []
