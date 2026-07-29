import httpx
from typing import Optional, Dict, Any

class MapeoClient:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    async def get_by_room(self, matrix_room_id: str) -> Optional[Dict[str, Any]]:
        """Busca el mapeo de una sala específica para saber a qué fork corresponde."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/mapeos/by-room/{matrix_room_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            response.raise_for_status()
