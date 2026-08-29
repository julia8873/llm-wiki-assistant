import asyncio
import base64
import os
import sys

# Append app to python path
sys.path.insert(0, "/app")

from app.services.git.github_provider import GitHubProvider
import httpx
import respx
import json

async def test_append_logic():
    config = {
        'git': {
            'organizacion': 'test-org',
            'github': {
                'api_base_url': 'https://api.github.com',
                'pat': 'fake-pat'
            },
            'repo_plantilla': 'test-template'
        }
    }
    
    provider = GitHubProvider(config)
    repo_url = "https://github.com/test-org/test-repo.git"
    path = "logs/discrepancias/2026-08-29.jsonl"
    new_content = '{"new": "data"}\n'
    message = "Audit: test append"
    
    # Existing content in base64
    existing_content = '{"old": "data"}\n'
    existing_content_b64 = base64.b64encode(existing_content.encode('utf-8')).decode('utf-8')
    
    print("Iniciando test de append...")
    
    with respx.mock(assert_all_called=True) as mocker:
        # Mock GET to return existing file
        get_route = mocker.get(f"https://api.github.com/repos/test-org/test-repo/contents/{path}")
        get_route.return_value = httpx.Response(200, json={
            "sha": "fake-old-sha",
            "content": existing_content_b64
        })
        
        # Mock PUT to verify payload
        put_route = mocker.put(f"https://api.github.com/repos/test-org/test-repo/contents/{path}")
        put_route.return_value = httpx.Response(200, json={
            "commit": {"sha": "fake-new-sha"}
        })
        
        commit_sha = await provider.crear_commit_archivo(repo_url, path, new_content, message)
        print(f"Commit SHA devuelto: {commit_sha}")
        
        # Verify that PUT was called exactly once
        assert put_route.called, "El PUT no fue llamado"
        
        # Get the request that was made to PUT
        request = put_route.calls[0].request
        payload = json.loads(request.content)
        
        sent_content_b64 = payload["content"]
        sent_content = base64.b64decode(sent_content_b64).decode('utf-8')
        
        print("--- Contenido enviado al API de GitHub ---")
        print(sent_content)
        print("------------------------------------------")
        
        expected_content = existing_content + new_content
        assert sent_content == expected_content, f"El contenido enviado no coincide con la concatenación esperada.\nEsperado:\n{expected_content}\nEnviado:\n{sent_content}"
        assert payload["sha"] == "fake-old-sha", "No se envió el SHA del archivo original para actualizarlo."
        
        print("✅ TEST SUPERADO: La lógica de append funciona y envía el SHA del archivo original.")

if __name__ == "__main__":
    asyncio.run(test_append_logic())
