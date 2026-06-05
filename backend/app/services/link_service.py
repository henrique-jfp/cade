import httpx
from app.clients.real_debrid_client import RealDebridClient

class LinkService:
    def __init__(self, rd_client: RealDebridClient):
        self.rd_client = rd_client

    async def resolve(self, magnet: str) -> dict:
        """Resolve a magnet to a direct link via RD."""
        # Se for um link direto (http), usa o unrestrictlink
        if magnet.startswith("http://") or magnet.startswith("https://"):
            return await self.resolve_direct_link(magnet)
            
        return await self.rd_client.resolve_magnet_to_direct_link(magnet)

    async def resolve_direct_link(self, link: str) -> dict:
        """Resolve a direct host link (ddownload, etc) using Real-Debrid unrestrict."""
        try:
            unrestricted = await self.rd_client.unrestrict_link(link)
            return {
                "success": True,
                "stream_url": unrestricted.get("download"),
                "download_url": unrestricted.get("download"),
                "filename": unrestricted.get("filename"),
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def fallback_direct_links(self, query: str) -> list[str]:
        """Fallback to scrape direct links from OnScreens/Archivebate if torrents are not found."""
        links = []
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return links

        query_normalized = query.replace(" ", "-").lower()
        
        # OnScreens Direct Links
        try:
            url_onscreens = f"https://www.onscreens.me/m/{query_normalized}"
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url_onscreens, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if any(host in href for host in ['ddownload.com', 'rapidgator.net', 'katfile.com', 'filefactory.com']):
                            links.append(href)
        except Exception:
            pass

        # Archivebate Direct Links
        try:
            url_ab = f"https://archivebate.com/profile/{query_normalized}"
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url_ab, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if any(host in href for host in ['ddownload.com', 'rapidgator.net', 'katfile.com']):
                            links.append(href)
        except Exception:
            pass

        return list(set(links))
