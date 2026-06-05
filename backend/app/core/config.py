from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Instant Media Search API"
    app_env: str = "dev"
    log_level: str = "info"

    real_debrid_api_key: str = ""
    real_debrid_base_url: str = "https://api.real-debrid.com/rest/1.0"

    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    jackett_base_url: str = ""
    jackett_api_key: str = ""

    sqlite_path: str = "./instant_cache.db"
    cache_ttl_minutes: int = 30
    max_search_results: int = 200
    allow_unverified_on_rd_forbidden: bool = True

    frontend_origin: str = "http://localhost:5173"


settings = Settings()
