import os
import httpx
from typing import Dict, Any, Optional

class LLMClientError(Exception):
    pass

class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def get_response(self, system_prompt: str, user_prompt: str, max_tokens_override: int = None) -> str:
        """! 
        @brief Obtiene una respuesta de texto del LLM.
        @param system_prompt Instrucciones de sistema.
        @param user_prompt Mensaje del usuario.
        @param max_tokens_override (Opcional) Sobrescribe el limite maximo de tokens para esta peticion especifica.
        @return Respuesta generada.
        """
        raise NotImplementedError("Subclasses must implement get_response")
        
    async def get_embedding(self, text: str) -> list[float]:
        raise NotImplementedError("Subclasses must implement get_embedding")

class OpenAICompatibleClient(LLMClient):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base_url = self.config.get("api_base_url")
        self.api_key_env_var = self.config.get("api_key_env_var")
        self.modelo = self.config.get("modelo_defecto")
        self.temperatura = self.config.get("temperatura", 0.2)
        self.max_tokens = self.config.get("max_tokens", 1024)
        self.top_p = self.config.get("top_p", 0.95)
        self.timeout = self.config.get("timeout_segundos", 60)
        
        env_key = os.environ.get(self.api_key_env_var) if self.api_key_env_var else None
        self.api_key = env_key or self.config.get("api_key") or self.api_key_env_var
        
        # Permitimos API keys dummy para proveedores que no lo exigen (ej. Ollama local)
        # Pero si el endpoint está vacío, fallamos.
        if not self.api_base_url:
            raise LLMClientError(f"api_base_url no configurada para el cliente OpenAI compatible")

    async def get_response(self, system_prompt: str, user_prompt: str, max_tokens_override: int = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperatura,
            "max_tokens": max_tokens_override if max_tokens_override else self.max_tokens,
            "top_p": self.top_p
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.api_base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                raise LLMClientError(f"Error HTTP del LLM: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise LLMClientError(f"Error de conexión con el LLM: {str(e)}")

    async def get_embedding(self, text: str) -> list[float]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Simple heuristic to determine embedding model
        embedding_model = "text-embedding-3-small"
        if "localhost" in self.api_base_url or "11434" in self.api_base_url:
            embedding_model = "nomic-embed-text" # Typical for Ollama
            
        if "groq.com" in self.api_base_url:
            # Groq API doesn't support embeddings currently.
            # Return a dummy vector so the flow doesn't crash.
            # Note: RAG retrieval will not be semantically accurate.
            return [0.1] * 1536
            
        payload = {
            "model": embedding_model,
            "input": text
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.api_base_url}/embeddings", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
            except Exception as e:
                raise LLMClientError(f"Error obteniendo embedding: {str(e)}")

class GeminiClient(LLMClient):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base_url = self.config.get("api_base_url")
        self.api_key_env_var = self.config.get("api_key_env_var")
        self.modelo = self.config.get("modelo_defecto")
        self.temperatura = self.config.get("temperatura", 0.2)
        self.max_tokens = self.config.get("max_tokens", 1024)
        self.top_p = self.config.get("top_p", 0.95)
        self.timeout = self.config.get("timeout_segundos", 60)
        
        env_key = os.environ.get(self.api_key_env_var) if self.api_key_env_var else None
        self.api_key = env_key or self.config.get("api_key") or self.api_key_env_var
        if not self.api_key:
            raise LLMClientError(f"API key requerida en la variable {self.api_key_env_var}")
            
    async def get_response(self, system_prompt: str, user_prompt: str, max_tokens_override: int = None) -> str:
        import logging
        logging.getLogger("llm_wiki.debug").error(f"SYSTEM PROMPT: {system_prompt}")
        url = f"{self.api_base_url}/models/{self.modelo}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "parts": [{"text": user_prompt}]
            }],
            "generationConfig": {
                "temperature": self.temperatura,
                "maxOutputTokens": max_tokens_override if max_tokens_override else self.max_tokens,
                "topP": self.top_p
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            max_retries = 3
            base_delay = 10
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    response_text = "".join([p.get("text", "") for p in data["candidates"][0]["content"]["parts"]])
                    logging.getLogger("llm_wiki.debug").error(f"MAX TOKENS CONF: {self.max_tokens}")
                    logging.getLogger("llm_wiki.debug").error(f"GEMINI RAW DATA: {data}")
                    return response_text
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        import asyncio
                        delay = base_delay * (2 ** attempt)
                        try:
                            error_data = e.response.json()
                            for detail in error_data.get("error", {}).get("details", []):
                                if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                                    delay_str = detail.get("retryDelay", "")
                                    if delay_str.endswith("s"):
                                        delay = float(delay_str[:-1])
                        except Exception:
                            pass
                        logging.getLogger("llm_wiki.debug").warning(f"Rate limit excedido (429). Reintentando en {delay}s... (Intento {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay + 1.0)
                        continue
                    raise LLMClientError(f"Error HTTP de Gemini: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    raise LLMClientError(f"Error de conexión con Gemini: {str(e)}")

    async def get_response_with_file(self, system_prompt: str, user_prompt: str, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        import base64
        b64_data = base64.b64encode(file_bytes).decode('utf-8')
        
        url = f"{self.api_base_url}/models/{self.modelo}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "parts": [
                    {"text": user_prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": self.temperatura,
                "maxOutputTokens": 8192,
                "topP": self.top_p
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            max_retries = 3
            base_delay = 10
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    response_text = "".join([p.get("text", "") for p in data["candidates"][0]["content"]["parts"]])
                    logging.getLogger("llm_wiki.debug").error(f"MAX TOKENS CONF: {self.max_tokens}")
                    logging.getLogger("llm_wiki.debug").error(f"GEMINI RAW DATA: {data}")
                    return response_text
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        import asyncio
                        delay = base_delay * (2 ** attempt)
                        try:
                            error_data = e.response.json()
                            for detail in error_data.get("error", {}).get("details", []):
                                if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                                    delay_str = detail.get("retryDelay", "")
                                    if delay_str.endswith("s"):
                                        delay = float(delay_str[:-1])
                        except Exception:
                            pass
                        logging.getLogger("llm_wiki.debug").warning(f"Rate limit excedido OCR (429). Reintentando en {delay}s... (Intento {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay + 1.0)
                        continue
                    raise LLMClientError(f"Error HTTP de Gemini OCR: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    raise LLMClientError(f"Error de conexion con Gemini OCR: {str(e)}")

    async def get_embedding(self, text: str) -> list[float]:
        url = f"{self.api_base_url}/models/gemini-embedding-2:embedContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": "models/gemini-embedding-2",
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            max_retries = 3
            base_delay = 5
            for attempt in range(max_retries):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data["embedding"]["values"]
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        import asyncio
                        import logging
                        delay = base_delay * (2 ** attempt)
                        logging.getLogger("llm_wiki.debug").warning(f"Rate limit excedido embedding (429). Reintentando en {delay}s... (Intento {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay + 1.0)
                        continue
                    raise LLMClientError(f"Error HTTP de Gemini embedding: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    raise LLMClientError(f"Error obteniendo embedding de Gemini: {str(e)}")

def get_llm_client(config: Dict[str, Any]) -> LLMClient:
    llm_config = config.get("llm", {})
    provider_name = llm_config.get("proveedor_activo", "openai")
    
    if provider_name not in llm_config:
        raise LLMClientError(f"Configuración para el proveedor {provider_name} no encontrada")
        
    provider_config = llm_config[provider_name]
    
    if provider_name in ["openai", "ollama"]:
        return OpenAICompatibleClient(provider_config)
    elif provider_name == "gemini":
        return GeminiClient(provider_config)
    else:
        raise LLMClientError(f"Proveedor LLM no soportado: {provider_name}")
