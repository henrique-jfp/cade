import httpx
import logging


class GoogleBooksClient:
    def __init__(self):
        self.headers = {"User-Agent": "CadeMediaSearch/1.0 (https://github.com/henrique-jfp/cade)"}

    async def search_metadata(self, query: str) -> dict:
        if not query or not query.strip():
            return {}

        clean_query = query.strip()

        # 1. Try Open Library API
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    "https://openlibrary.org/search.json",
                    params={"q": clean_query, "limit": 1},
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    docs = data.get("docs") or []
                    if docs:
                        top = docs[0]
                        title = top.get("title")
                        authors = top.get("author_name") or []
                        year_val = top.get("first_publish_year")
                        year = str(year_val) if year_val else None
                        cover_i = top.get("cover_i")
                        poster_url = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else None
                        subjects = top.get("subject") or []

                        return {
                            "title": title,
                            "year": year,
                            "synopsis": f"Autor(es): {', '.join(authors)}" if authors else None,
                            "poster_url": poster_url,
                            "rating": None,
                            "genres": (authors[:2] + subjects[:1]) if subjects else authors[:2],
                        }
        except Exception as exc:
            logging.warning(f"OpenLibrary metadata search failed for '{query}': {exc}")

        # 2. Fallback to Google Books API
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params={"q": clean_query, "maxResults": 1, "printType": "books"},
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items") or []
                    if items:
                        volume_info = items[0].get("volumeInfo") or {}
                        title = volume_info.get("title")
                        authors = volume_info.get("authors") or []
                        published_date = volume_info.get("publishedDate") or ""
                        year = published_date[:4] if len(published_date) >= 4 else None
                        description = volume_info.get("description")
                        image_links = volume_info.get("imageLinks") or {}
                        poster_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
                        if poster_url and poster_url.startswith("http://"):
                            poster_url = poster_url.replace("http://", "https://", 1)

                        rating = volume_info.get("averageRating")
                        categories = volume_info.get("categories") or []

                        return {
                            "title": title,
                            "year": year,
                            "synopsis": description,
                            "poster_url": poster_url,
                            "rating": rating,
                            "genres": authors[:2] + categories[:1],
                        }
        except Exception as exc:
            logging.warning(f"GoogleBooksClient search failed for '{query}': {exc}")

        return {}
