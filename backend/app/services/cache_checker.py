from app.clients.real_debrid_client import RealDebridClient
from app.db.cache_repo import CacheRepository


def _is_rd_payload_cached(payload: dict) -> bool:
    if not payload:
        return False

    rd = payload.get("rd")
    if isinstance(rd, list) and rd:
        return True
    if isinstance(rd, dict) and rd:
        return True

    for key in payload:
        nested = payload.get(key)
        if isinstance(nested, dict):
            rd_nested = nested.get("rd")
            if isinstance(rd_nested, (list, dict)) and rd_nested:
                return True
    return False


class CacheChecker:
    def __init__(self, cache_repo: CacheRepository, rd_client: RealDebridClient):
        self.cache_repo = cache_repo
        self.rd_client = rd_client

    async def filter_cached_hashes(self, hashes: list[str]) -> set[str]:
        if not hashes:
            return set()

        cached_rows = self.cache_repo.get_many(hashes)
        cached_hashes = {h for h, v in cached_rows.items() if v.get("is_cached")}

        missing = [h for h in hashes if h not in cached_rows]
        if not missing:
            return cached_hashes

        rd_payloads = await self.rd_client.get_instant_availability(missing)

        upsert_payload: dict[str, dict] = {}
        for h in missing:
            payload = rd_payloads.get(h, {})
            is_cached = _is_rd_payload_cached(payload)
            upsert_payload[h] = {"is_cached": is_cached, "payload": payload}
            if is_cached:
                cached_hashes.add(h)

        self.cache_repo.upsert_many(upsert_payload)
        return cached_hashes
