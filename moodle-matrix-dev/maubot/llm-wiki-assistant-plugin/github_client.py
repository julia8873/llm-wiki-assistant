"""! @file github_client.py
@brief Utilidades y definiciones para interactuar con la API HTTP de GitHub desde el worker.

NOTA ARQUITECTÓNICA:
Esta clase de excepción `GitHubRateLimitError` tiene la misma estructura que la definida
en `mapeo-api/app/services/git/base.py`. La separación y duplicación de esta clase no
es accidental: `mapeo-api` y `maubot` (worker) operan en contenedores Docker aislados
con volúmenes distintos, y los mecanismos de detección son diferentes (HTTP directo en
`mapeo-api` vs. parseo de stderr del cliente binario `git` en este worker).
"""

import httpx
import logging
import os
import time

logger = logging.getLogger(__name__)

class GitHubRateLimitError(Exception):
    """!
    @brief Error específico de Rate Limit detectado durante operaciones en el worker.
    """
    def __init__(self, message: str, retry_after_seconds: int):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds

async def get_opportunistic_reset_time() -> int:
    """!
    @brief Consulta el endpoint /rate_limit de GitHub de forma oportunista.
    @return Segundos de espera hasta el reset, o 0 si no está limitado (o falla la comprobación).
    """
    pat = os.getenv("GITHUB_PAT")
    if not pat:
        return 0
        
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.github.com/rate_limit", 
                headers={"Authorization": f"token {pat}", "Accept": "application/vnd.github.v3+json"},
                timeout=5.0
            )
            if res.status_code == 200:
                data = res.json()
                core = data.get("resources", {}).get("core", {})
                if core.get("remaining") == 0:
                    reset_ts = core.get("reset", 0)
                    wait = max(int(reset_ts) - int(time.time()), 0)
                    return wait
    except Exception as e:
        logger.warning(f"Error consultando /rate_limit de forma oportunista: {e}")
    
    return 0
