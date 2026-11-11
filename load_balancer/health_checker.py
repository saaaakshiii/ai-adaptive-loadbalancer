import asyncio
import httpx

async def collect_backend_metrics(client: httpx.AsyncClient, backends):
    async def one(backend):
        try:
            health = await client.get(f"{backend['url']}/health", timeout=0.8)
            if health.status_code != 200:
                return False, {}
            response = await client.get(f"{backend['url']}/metrics", timeout=0.8)
            response.raise_for_status()
            return True, response.json()
        except (httpx.HTTPError, ValueError):
            return False, {}
    return await asyncio.gather(*(one(b) for b in backends))
