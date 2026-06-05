import asyncio

import httpx


class RealDebridAuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class RealDebridApiError(Exception):
    pass


class RealDebridClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _raise_for_status(self, response: httpx.Response):
        if response.status_code == 401:
            raise RealDebridAuthError("Token do Real-Debrid inválido ou expirado.", status_code=401)
        if response.status_code == 403:
            raise RealDebridAuthError(
                "A conta não tem permissão para usar instantAvailability (ex.: plano sem suporte/premium).",
                status_code=403,
            )
        if response.status_code >= 400:
            raise RealDebridApiError(f"Erro Real-Debrid: HTTP {response.status_code}")

    async def get_instant_availability(self, infohashes: list[str]) -> dict[str, dict]:
        if not self.api_key or not infohashes:
            return {}

        results: dict[str, dict] = {}
        async with httpx.AsyncClient(timeout=20) as client:
            for infohash in infohashes:
                url = f"{self.base_url}/torrents/instantAvailability/{infohash}"
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 404:
                    results[infohash] = {}
                    continue
                self._raise_for_status(resp)
                data = resp.json()
                results[infohash] = data.get(infohash, data)
        return results

    async def add_magnet(self, magnet: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.base_url}/torrents/addMagnet",
                headers=self._headers(),
                data={"magnet": magnet},
            )
            self._raise_for_status(resp)
            return resp.json()

    async def select_files(self, torrent_id: str, files: str = "all") -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.base_url}/torrents/selectFiles/{torrent_id}",
                headers=self._headers(),
                data={"files": files},
            )
            self._raise_for_status(resp)
            return {"status": "ok"}

    async def get_torrent_info(self, torrent_id: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{self.base_url}/torrents/info/{torrent_id}", headers=self._headers())
            self._raise_for_status(resp)
            return resp.json()

    async def unrestrict_link(self, link: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.base_url}/unrestrict/link",
                headers=self._headers(),
                data={"link": link},
            )
            self._raise_for_status(resp)
            return resp.json()

    async def resolve_magnet_to_direct_link(self, magnet: str, max_wait_seconds: int = 20) -> dict:
        add_result = await self.add_magnet(magnet)
        torrent_id = str(add_result.get("id", ""))
        if not torrent_id:
            return {"success": False, "message": "Real-Debrid não retornou id do torrent."}

        await self.select_files(torrent_id, "all")

        elapsed = 0
        while elapsed < max_wait_seconds:
            info = await self.get_torrent_info(torrent_id)
            links = info.get("links") or []
            if links:
                unrestricted = await self.unrestrict_link(links[0])
                return {
                    "success": True,
                    "stream_url": unrestricted.get("download"),
                    "download_url": unrestricted.get("download"),
                    "filename": unrestricted.get("filename") or info.get("filename"),
                }

            await asyncio.sleep(2)
            elapsed += 2

        return {
            "success": False,
            "message": "Tempo limite ao resolver magnet. Tente novamente em alguns segundos.",
        }
