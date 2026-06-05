from functools import lru_cache

from app.clients.real_debrid_client import RealDebridClient
from app.clients.tmdb_client import TmdbClient
from app.core.config import Settings, settings
from app.db.cache_repo import CacheRepository
from app.services.cache_checker import CacheChecker
from app.services.link_service import LinkService


def get_settings() -> Settings:
    return settings


@lru_cache
def _cache_repo() -> CacheRepository:
    return CacheRepository(settings.sqlite_path, ttl_minutes=settings.cache_ttl_minutes)


@lru_cache
def _rd_client() -> RealDebridClient:
    return RealDebridClient(settings.real_debrid_base_url, settings.real_debrid_api_key)


@lru_cache
def _tmdb_client() -> TmdbClient:
    return TmdbClient(settings.tmdb_base_url, settings.tmdb_api_key)


def get_cache_checker() -> CacheChecker:
    return CacheChecker(_cache_repo(), _rd_client())


def get_tmdb_client() -> TmdbClient:
    return _tmdb_client()


def get_link_service() -> LinkService:
    return LinkService(_rd_client())
