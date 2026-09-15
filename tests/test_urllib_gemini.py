import urllib.request
import json

import os
api_key = os.environ.get("GEMINI_API_KEY", "tu-api-key")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"

system_prompt = """Eres un asistente docente. Tu función principal es responder preguntas
basándote EXCLUSIVAMENTE en el contexto recuperado de los ficheros OKF
del repositorio del alumno vinculado a esta sala. Puedes interactuar de
forma natural y educada (saludar, despedirte, etc.), pero cuando se te
pregunte por información de la asignatura o conceptos, debes seguir estas reglas:

Reglas estrictas:
1. Responde solo con información presente en el contexto recuperado.
   Si la información solicitada no aparece, dilo explícitamente con:
   'No he encontrado información sobre esto en tu repositorio.'

Contexto recuperado:
--- Chunk 1 (Fichero: profesores/profesor1/okf/concepts/teorema-existencia-unicidad.md) ---
El teorema de existencia y unicidad establece que si la función F es Lipschitz...
"""
user_prompt = "Pregunta: que sabes sobre el teorema de existencia y unicidad?"

payload = {
    "systemInstruction": {
        "parts": [{"text": system_prompt}]
    },
    "contents": [{
        "parts": [{"text": user_prompt}]
    }],
    "generationConfig": {
        "temperature": 0.2,
        "maxOutputTokens": 1024,
        "topP": 0.95
    }
}

req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode('utf-8')}")
