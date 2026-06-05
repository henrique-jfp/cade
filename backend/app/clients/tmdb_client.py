import httpx


class TmdbClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def search_metadata(self, query: str) -> dict:
        if not self.api_key or not query.strip():
            return {}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.base_url}/search/multi",
                params={"api_key": self.api_key, "query": query, "include_adult": "false"},
            )
            if resp.status_code != 200:
                return {}

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return {}

            top = results[0]
            title = top.get("title") or top.get("name")
            year_src = top.get("release_date") or top.get("first_air_date") or ""
            year = year_src[:4] if year_src else None
            poster_path = top.get("poster_path")
            rating = top.get("vote_average")
            genre_ids = top.get("genre_ids") or []
            genres = self._map_genre_ids(genre_ids)

            return {
                "title": title,
                "year": year,
                "synopsis": top.get("overview"),
                "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
                "rating": rating,
                "genres": genres,
            }

    def _map_genre_ids(self, ids: list[int]) -> list[str]:
        genre_map = {
            28: "Action",
            12: "Adventure",
            16: "Animation",
            35: "Comedy",
            80: "Crime",
            99: "Documentary",
            18: "Drama",
            10751: "Family",
            14: "Fantasy",
            36: "History",
            27: "Horror",
            10402: "Music",
            9648: "Mystery",
            10749: "Romance",
            878: "Sci-Fi",
            10770: "TV",
            53: "Thriller",
            10752: "War",
            37: "Western",
        }
        return [genre_map.get(gid, "") for gid in ids if gid in genre_map][:3]
