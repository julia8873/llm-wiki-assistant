import asyncio, httpx

async def test():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://host.docker.internal:<OLLAMA_PORT>/v1/models")
            print(f"Status: {r.status_code}")
            print(r.text)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
