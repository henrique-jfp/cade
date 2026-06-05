import httpx
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.models.schemas import TorrentResult
from app.services.hash_extractor import extract_infohash, infer_resolution

# ... (rest of the helper functions remain the same)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _format_size(size_bytes: int | None) -> str | None:
    if not size_bytes:
        return None
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    return f"{size:.1f} {units[idx]}"


def _infer_category(title: str, source_category: str | None = None) -> str:
    if source_category:
        return source_category
    lowered = title.lower()
    if any(word in lowered for word in ['cam4','chaturbate','replay','recording','cam']):
        return 'Cam'
    if any(word in lowered for word in ["game", "crack", "repack", "gog", "steam"]):
        return "Games"
    if any(word in lowered for word in ["xxx", "porn", "adult"]):
        return "Adult"
    if any(word in lowered for word in ["mp3", "flac", "album", "music"]):
        return "Music"
    if any(word in lowered for word in ["s0", "season", "episode"]):
        return "TV"
    if any(word in lowered for word in ["bluray", "1080p", "2160p", "4k", "remux"]):
        return "Movies"
    if any(word in lowered for word in ["software", "windows", "adobe"]):
        return "Software"
    if any(word in lowered for word in ["sport", "match", "game", "nba", "fifa", "ufc"]):
        # Note: "game" is also in Games, so order matters. Sports should probably check for specific sport terms.
        if any(sport in lowered for sport in ["football", "soccer", "nba", "basketball", "ufc", "f1", "formula"]):
            return "Sports"
    return "Other"


async def search_apibay(query: str, limit: int = 30) -> list[TorrentResult]:
    url = "https://apibay.org/q.php"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"q": query})
        if resp.status_code != 200:
            return []

        data = resp.json()
        items: list[TorrentResult] = []
        for raw in data[:limit]:
            infohash = (raw.get("info_hash") or "").lower()
            if len(infohash) != 40:
                continue

            name = raw.get("name") or "Sem título"
            magnet = f"magnet:?xt=urn:btih:{infohash}&dn={name}"
            size_bytes = _safe_int(raw.get("size"), None)
            upload_timestamp = _safe_int(raw.get("added"), 0)
            uploaded_at = None
            if upload_timestamp > 0:
                from datetime import datetime, timezone

                uploaded_at = datetime.fromtimestamp(upload_timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

            items.append(
                TorrentResult(
                    title=name,
                    infohash=infohash,
                    magnet=magnet,
                    source="apibay",
                    seeders=_safe_int(raw.get("seeders")),
                    leechers=_safe_int(raw.get("leechers")),
                    size_bytes=size_bytes,
                    size_label=_format_size(size_bytes),
                    resolution=infer_resolution(name),
                    category=_infer_category(name),
                    uploaded_at=uploaded_at,
                )
            )
        return items


def _media_type_to_jackett_categories(media_type: str) -> list[str]:
    normalized = (media_type or "all").lower()
    mapping = {
        "all": [],
        "movie": ["2000"],
        "series": ["5000"],
        "tv": ["5000"],
        "anime": ["5070"],
        "music": ["3000"],
        "game": ["1000", "1010", "1020", "1030", "1040", "1050"],  # All console/platform games
        "software": ["4000"],
        "adult": ["6000", "6010", "6020", "6030", "6040", "6050", "6060", "6070"],
        "porn": ["6000", "6010", "6020", "6030", "6040", "6050", "6060", "6070"],
        "books": ["7000"],
        "sports": ["5040"],
    }
    return mapping.get(normalized, [])


async def search_youtube_titles(query: str, limit: int = 5) -> list[str]:
    """Search YouTube for the query and return a list of video titles."""
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_utils': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We use ytsearch to find videos
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch{limit}:{query}", download=False)
            titles = [entry.get('title') for entry in info.get('entries', []) if entry.get('title')]
            return titles
    except Exception as e:
        logging.warning(f"YouTube title search failed: {e}")
        return []


async def search_jackett(query: str, media_type: str = "all", limit: int = 120) -> list[TorrentResult]:
    if not settings.jackett_base_url or not settings.jackett_api_key:
        return []

    url = f"{settings.jackett_base_url.rstrip('/')}/api/v2.0/indexers/all/results"
    params: dict[str, str | list[str]] = {
        "apikey": settings.jackett_api_key,
        "Query": query,
        "Category[]": _media_type_to_jackett_categories(media_type),
    }

    # Retry logic for Jackett (2 attempts)
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    if attempt == 0:
                        continue
                    return []

                data = resp.json()
                rows = data.get("Results") or []
                items: list[TorrentResult] = []

                for raw in rows[:limit]:
                    infohash = (raw.get("InfoHash") or "").lower()
                    magnet = raw.get("MagnetUri") or raw.get("Link")
                    if not infohash:
                        infohash = extract_infohash(magnet or "") or ""
                    if len(infohash) != 40:
                        continue

                    title = raw.get("Title") or "Sem título"
                    size_bytes = _safe_int(raw.get("Size"), None)
                    tracker = raw.get("Tracker") or "jackett"
                    category_desc = (raw.get("CategoryDesc") or "Other").split("/")[-1].strip()
                    publish_date = raw.get("PublishDate", "")[:10] if raw.get("PublishDate") else None

                    items.append(
                        TorrentResult(
                            title=title,
                            infohash=infohash,
                            magnet=magnet,
                            source=f"jackett:{tracker}",
                            seeders=_safe_int(raw.get("Seeders")),
                            leechers=_safe_int(raw.get("Peers")),
                            size_bytes=size_bytes,
                            size_label=_format_size(size_bytes),
                            resolution=infer_resolution(title),
                            category=category_desc or _infer_category(title),
                            uploaded_at=publish_date,
                        )
                    )
                return items
        except Exception:
            if attempt == 0:
                continue
            return []

    return []


async def search_1337x(query: str, limit: int = 30) -> list[TorrentResult]:
    """Search 1337x via alternative API"""
    url = "https://1337x.to/search/{}/1/".format(query.replace(" ", "+"))
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Note: This is a simplified version - in production you'd scrape the HTML
            # For now, we'll use a public API mirror if available
            api_url = f"https://1337x.unblockit.blue/api/search/{query}/1"
            resp = await client.get(api_url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            items: list[TorrentResult] = []
            
            for raw in (data.get("list") or [])[:limit]:
                magnet = raw.get("magnet")
                infohash = extract_infohash(magnet or "") or ""
                if len(infohash) != 40:
                    continue
                
                title = raw.get("name") or "Sem título"
                size_str = raw.get("size") or ""
                
                items.append(
                    TorrentResult(
                        title=title,
                        infohash=infohash,
                        magnet=magnet,
                        source="1337x",
                        seeders=_safe_int(raw.get("seeds")),
                        leechers=_safe_int(raw.get("leeches")),
                        size_bytes=None,
                        size_label=size_str,
                        resolution=infer_resolution(title),
                        category=_infer_category(title),
                        uploaded_at=raw.get("added"),
                    )
                )
            return items
    except Exception:
        return []


async def search_eztv(query: str, limit: int = 30) -> list[TorrentResult]:
    """Search EZTV for TV shows"""
    url = "https://eztv.re/api/get-torrents"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={"limit": limit, "page": 0, "imdb_id": query})
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            torrents = data.get("torrents") or []
            items: list[TorrentResult] = []
            
            for raw in torrents[:limit]:
                infohash = (raw.get("hash") or "").lower()
                if len(infohash) != 40:
                    continue
                
                title = raw.get("title") or "Sem título"
                if query.lower() not in title.lower():
                    continue
                
                magnet = raw.get("magnet_url")
                size_bytes = _safe_int(raw.get("size_bytes"))
                
                items.append(
                    TorrentResult(
                        title=title,
                        infohash=infohash,
                        magnet=magnet,
                        source="eztv",
                        seeders=_safe_int(raw.get("seeds")),
                        leechers=_safe_int(raw.get("peers")),
                        size_bytes=size_bytes,
                        size_label=_format_size(size_bytes),
                        resolution=infer_resolution(title),
                        category="TV",
                        uploaded_at=raw.get("date_released_unix"),
                    )
                )
            return items
    except Exception:
        return []


async def search_torrentgalaxy(query: str, limit: int = 30) -> list[TorrentResult]:
    """Search TorrentGalaxy"""
    url = f"https://torrentgalaxy.to/torrents.php"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            params = {"search": query, "sort": "seeders", "order": "desc"}
            resp = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return []
            
            # Note: In production, you'd parse HTML here or use their API if available
            # For now returning empty to avoid scraping complexity
            return []
    except Exception:
        return []


async def search_sukebei(query: str, limit: int = 60) -> list[TorrentResult]:
    """Search Sukebei (Nyaa adult section) for adult content"""
    url = "https://sukebei.nyaa.si/"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Use RSS feed for simplicity
            rss_url = "https://sukebei.nyaa.si/?page=rss&q=" + query.replace(" ", "+")
            resp = await client.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return []
            
            import re
            items: list[TorrentResult] = []
            
            # Extract torrent info from RSS
            pattern = r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<nyaa:seeders>(.*?)</nyaa:seeders>.*?<nyaa:leechers>(.*?)</nyaa:leechers>.*?<nyaa:size>(.*?)</nyaa:size>.*?</item>'
            matches = re.findall(pattern, resp.text, re.DOTALL)
            
            for match in matches[:limit]:
                title, link, seeders, leechers, size = match
                infohash = extract_infohash(link) or ""
                if len(infohash) != 40:
                    continue
                
                items.append(
                    TorrentResult(
                        title=title.strip(),
                        infohash=infohash,
                        magnet=link if link.startswith("magnet:") else f"magnet:?xt=urn:btih:{infohash}",
                        source="sukebei",
                        seeders=_safe_int(seeders),
                        leechers=_safe_int(leechers),
                        size_bytes=None,
                        size_label=size.strip(),
                        resolution=infer_resolution(title),
                        category="Adult",
                    )
                )
            return items
    except Exception:
        return []


async def search_sumo_adult(query: str, limit: int = 30) -> list[TorrentResult]:
    """Search SumoTorrent adult category"""
    # SumoTorrent doesn't have public API - would need scraping
    # Placeholder for future implementation
    return []


async def search_pornbay(query: str, limit: int = 60) -> list[TorrentResult]:
    """Search ThePornBay (TPB adult mirror)"""
    url = "https://apibay.org/q.php"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            full_query = query
            resp = await client.get(url, params={"q": full_query, "cat": "500"})  # Adult category
            if resp.status_code != 200:
                return []

            data = resp.json()
            items: list[TorrentResult] = []
            
            for raw in data[:limit]:
                infohash = (raw.get("info_hash") or "").lower()
                if len(infohash) != 40:
                    continue

                name = raw.get("name") or "Sem título"
                magnet = f"magnet:?xt=urn:btih:{infohash}&dn={name}"
                size_bytes = _safe_int(raw.get("size"), None)
                upload_timestamp = _safe_int(raw.get("added"), 0)
                uploaded_at = None
                if upload_timestamp > 0:
                    from datetime import datetime, timezone
                    uploaded_at = datetime.fromtimestamp(upload_timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

                items.append(
                    TorrentResult(
                        title=name,
                        infohash=infohash,
                        magnet=magnet,
                        source="pornbay",
                        seeders=_safe_int(raw.get("seeders")),
                        leechers=_safe_int(raw.get("leechers")),
                        size_bytes=size_bytes,
                        size_label=_format_size(size_bytes),
                        resolution=infer_resolution(name),
                        category="Adult",
                        uploaded_at=uploaded_at,
                    )
                )
            return items
    except Exception:
        return []


async def search_nyaa(query: str, limit: int = 30) -> list[TorrentResult]:
    """Search Nyaa for anime/asian content"""
    url = "https://nyaa.si/"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            params = {"f": 0, "c": "0_0", "q": query, "s": "seeders", "o": "desc"}
            resp = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return []
            
            # Simplified - would need HTML parsing in production
            # For now, using RSS feed
            rss_url = "https://nyaa.si/?page=rss&q=" + query.replace(" ", "+")
            resp = await client.get(rss_url)
            if resp.status_code != 200:
                return []
            
            # Basic RSS parsing - would use proper XML parser in production
            import re
            items: list[TorrentResult] = []
            
            # Extract torrent info from RSS
            pattern = r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<nyaa:seeders>(.*?)</nyaa:seeders>.*?<nyaa:leechers>(.*?)</nyaa:leechers>.*?<nyaa:size>(.*?)</nyaa:size>.*?</item>'
            matches = re.findall(pattern, resp.text, re.DOTALL)
            
            for match in matches[:limit]:
                title, link, seeders, leechers, size = match
                infohash = extract_infohash(link) or ""
                if len(infohash) != 40:
                    continue
                
                items.append(
                    TorrentResult(
                        title=title.strip(),
                        infohash=infohash,
                        magnet=link if link.startswith("magnet:") else f"magnet:?xt=urn:btih:{infohash}",
                        source="nyaa",
                        seeders=_safe_int(seeders),
                        leechers=_safe_int(leechers),
                        size_bytes=None,
                        size_label=size.strip(),
                        resolution=infer_resolution(title),
                        category="Anime",
                    )
                )
            return items
    except Exception:
        return []


async def search_yts(query: str, limit: int = 30) -> list[TorrentResult]:
    url = "https://yts.mx/api/v2/list_movies.json"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"query_term": query, "limit": 20})
        if resp.status_code != 200:
            return []

        payload = resp.json()
        movies = ((payload or {}).get("data") or {}).get("movies") or []
        items: list[TorrentResult] = []

        for movie in movies:
            title = movie.get("title") or "Sem título"
            year = movie.get("year")
            torrents = movie.get("torrents") or []

            for tor in torrents:
                infohash = (tor.get("hash") or "").lower()
                if len(infohash) != 40:
                    continue
                quality = tor.get("quality")
                display_title = f"{title} {year or ''} {quality or ''}".strip()
                magnet = f"magnet:?xt=urn:btih:{infohash}&dn={display_title}"
                size_label = tor.get("size")
                imdb_rating = movie.get("rating")

                items.append(
                    TorrentResult(
                        title=display_title,
                        infohash=infohash,
                        magnet=magnet,
                        source="yts",
                        seeders=0,
                        leechers=0,
                        size_bytes=None,
                        size_label=size_label,
                        resolution=infer_resolution(display_title),
                        category="Movies",
                        imdb_rating=imdb_rating,
                    )
                )

                if len(items) >= limit:
                    return items

        return items


async def search_cam_archives(query: str, limit: int = 30) -> list[TorrentResult]:
    """Search for camgirls replays/archives on OnScreens and Archivebate."""
    items: list[TorrentResult] = []
    
    # Needs beautifulsoup4
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    # 1. OnScreens
    try:
        query_normalized = query.replace(" ", "-").lower()
        url_onscreens = f"https://www.onscreens.me/m/{query_normalized}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url_onscreens, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if href.startswith('magnet:?'):
                        title = "Cam Replay"
                        # Try to find a title in a nearby element
                        row = link.find_parent('tr')
                        if row:
                            title_cell = row.find('td')
                            if title_cell:
                                title = title_cell.get_text(strip=True) or title
                        else:
                            parent_div = link.find_parent('div')
                            if parent_div:
                                title = parent_div.get_text(strip=True)[:50] or title

                        infohash = extract_infohash(href)
                        if infohash and len(infohash) == 40:
                            items.append(
                                TorrentResult(
                                    title=title,
                                    infohash=infohash,
                                    magnet=href,
                                    source="onscreens",
                                    seeders=1,
                                    leechers=0,
                                    category="Cam"
                                )
                            )
                        if len(items) >= limit:
                            break
    except Exception as e:
        import logging
        logging.warning(f"OnScreens scrape failed: {e}")

    # If we got enough, return early
    if len(items) >= limit:
        return items[:limit]

    # 2. Archivebate (Fallback)
    try:
        query_ab = query.replace(" ", "-").lower()
        url_ab = f"https://archivebate.com/profile/{query_ab}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url_ab, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if href.startswith('magnet:?'):
                        title = link.get_text(strip=True) or f"{query_ab} archivebate video"
                        infohash = extract_infohash(href)
                        if infohash and len(infohash) == 40:
                            items.append(
                                TorrentResult(
                                    title=title,
                                    infohash=infohash,
                                    magnet=href,
                                    source="archivebate",
                                    seeders=1,
                                    leechers=0,
                                    category="Cam"
                                )
                            )
                        if len(items) >= limit:
                            break
    except Exception as e:
        import logging
        logging.warning(f"Archivebate scrape failed: {e}")

    return items[:limit]

async def search_all(query: str, media_type: str = "all", max_results: int = 150) -> list[TorrentResult]:
    media = (media_type or "all").lower()

    # For games, enhance query with popular release groups to increase chances of finding cracks/repacks
    if media == "game":
        query = f"{query} (dodi OR fitgirl OR steamrip OR repack OR crack)"
        
    if media == "adult":
        query = f"{query} (cam4 OR chaturbate OR replay OR recording OR archive OR cam)"

    # If searching for old sports matches, first get potential titles from YouTube
    youtube_queries = []
    if media == "sports":
        logging.info(f"Sports search detected. Querying YouTube for titles related to '{query}'")
        youtube_titles = await search_youtube_titles(query, limit=5)
        if youtube_titles:
            logging.info(f"Found potential YouTube titles: {youtube_titles}")
            youtube_queries.extend(youtube_titles)

    # Prioritize Jackett (covers multiple indexers if configured) with higher limit
    providers = []
    
    # Add searches for each YouTube title found
    for yt_query in youtube_queries:
        providers.append((search_jackett, [yt_query, media, int(max_results * 1.5)]))
        providers.append((search_apibay, [yt_query, max_results]))
        providers.append((search_1337x, [yt_query, max_results]))

    # Also add the original query
    providers.append((search_jackett, [query, media, int(max_results * 1.5)]))
    providers.append((search_apibay, [query, max_results]))
    providers.append((search_1337x, [query, max_results]))
    
    # Add specialized providers based on media type
    if media in {"all", "movie"}:
        providers.append((search_yts, [query, max_results]))
    
    if media in {"all", "series", "tv"}:
        providers.append((search_eztv, [query, max_results]))
    
    if media in {"all", "anime"}:
        providers.append((search_nyaa, [query, max_results]))
    
    # Add adult content indexers
    if media in {"all", "adult", "porn"}:
        providers.append((search_cam_archives, [query, max_results]))
        providers.append((search_sukebei, [query, max_results]))
        providers.append((search_pornbay, [query, max_results]))

    import asyncio
    import logging

    async def run_provider(provider_func, args):
        try:
            return await asyncio.wait_for(provider_func(*args), timeout=8.0)
        except asyncio.TimeoutError:
            logging.warning(f"Provider {provider_func.__name__} timed out")
            return []
        except Exception as e:
            logging.error(f"Provider {provider_func.__name__} failed: {e}")
            return []

    # Run all providers in parallel
    tasks = [run_provider(p, args) for p, args in providers]
    results_lists = await asyncio.gather(*tasks)
    
    all_results: list[TorrentResult] = []
    for res_list in results_lists:
        all_results.extend(res_list)

    unique: dict[str, TorrentResult] = {}
    for item in all_results:
        normalized_hash = extract_infohash(item.infohash or item.magnet or "")
        if not normalized_hash:
            continue
        if normalized_hash not in unique:
            item.infohash = normalized_hash
            unique[normalized_hash] = item

    return list(unique.values())[:max_results]
