from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.real_debrid_client import RealDebridApiError, RealDebridAuthError
from app.clients.tmdb_client import TmdbClient
from app.core.config import Settings
from app.models.schemas import Metadata, SearchResponse, SearchResultItem, TorrentResult
from app.services.cache_checker import CacheChecker
from app.services.real_deps import get_cache_checker, get_settings, get_tmdb_client
from app.services.result_ranker import rank_results
from app.services.torrent_searcher import search_all

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Termo de busca"),
    media_type: str = Query("all", description="all|movie|series|game|music|software|adult|anime|books|sports"),
    app_settings: Settings = Depends(get_settings),
    cache_checker: CacheChecker = Depends(get_cache_checker),
    tmdb_client: TmdbClient = Depends(get_tmdb_client),
):
    torrents = await search_all(q, media_type=media_type, max_results=app_settings.max_search_results)
    ranked = rank_results(torrents)

    hashes = [t.infohash for t in ranked]
    warning: str | None = None
    try:
        cached_hashes = await cache_checker.filter_cached_hashes(hashes)
    except RealDebridAuthError as exc:
        if exc.status_code == 403 and app_settings.allow_unverified_on_rd_forbidden:
            cached_hashes = set()
            warning = (
                "Sua conta Real-Debrid não permite instantAvailability no momento. "
                "Mostrando resultados não verificados."
            )
        else:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except RealDebridApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    instant_items: list[TorrentResult] = [t for t in ranked if t.infohash in cached_hashes]
    fallback_items: list[TorrentResult] = ranked if warning else []
    items_to_render = instant_items if instant_items else fallback_items

    metadata_map: dict[str, Metadata] = {}
    normalized_media = (media_type or "all").lower()
    can_enrich_with_tmdb = normalized_media in {"movie", "series", "tv"}

    if can_enrich_with_tmdb and app_settings.tmdb_api_key:
        for item in items_to_render[:5]:
            if item.title in metadata_map:
                continue
            md = await tmdb_client.search_metadata(item.title)
            metadata_map[item.title] = Metadata(**md) if md else Metadata(title=item.title)

    response_items = [
        SearchResultItem(
            title=t.title,
            source=t.source,
            infohash=t.infohash,
            magnet=t.magnet,
            seeders=t.seeders,
            leechers=t.leechers,
            size_label=t.size_label,
            resolution=t.resolution,
            category=t.category,
            uploaded_at=t.uploaded_at,
            instant_available=t.infohash in cached_hashes,
            metadata=metadata_map.get(t.title, Metadata(title=t.title, rating=t.imdb_rating)),
        )
        for t in items_to_render
    ]

    return SearchResponse(
        query=q,
        total_found=len(ranked),
        total_instant=len([i for i in response_items if i.instant_available]),
        items=response_items,
        warning=warning,
    )
