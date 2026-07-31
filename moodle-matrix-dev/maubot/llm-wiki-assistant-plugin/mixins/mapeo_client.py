import httpx
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("llm_wiki.mapeo_client")

class MapeoClientError(Exception):
    pass

class MapeoClient:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url.rstrip('/')
        self.token = token

    async def get_room_mapping(self, matrix_room_id: str) -> Dict[str, Any]:
        """
        Devuelve el diccionario completo del mapeo para una sala Matrix específica.
        Si la sala no está mapeada, levanta MapeoClientError.
        """
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{self.api_url}/mapeos/by-room/{matrix_room_id}"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    raise MapeoClientError(f"La sala {matrix_room_id} no está vinculada a ningún repositorio.")
                    
                response.raise_for_status()
                data = response.json()
                
                repo_url = data.get("repo_url")
                git_provider = data.get("git_provider")
                
                if not repo_url or not git_provider:
                    raise MapeoClientError("La respuesta de Mapeo API está incompleta.")
                    
                return data
                
            except httpx.HTTPStatusError as e:
                raise MapeoClientError(f"Error HTTP de Mapeo API: {e.response.status_code}")
            except Exception as e:
                if isinstance(e, MapeoClientError):
                    raise
                raise MapeoClientError(f"Error de conexión con Mapeo API: {str(e)}")
