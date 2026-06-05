from app.models.schemas import TorrentResult


RESOLUTION_SCORE = {
    "2160p": 5,
    "1080p": 4,
    "720p": 3,
    "480p": 2,
    None: 1,
}


def rank_results(items: list[TorrentResult]) -> list[TorrentResult]:
    def score(item: TorrentResult) -> tuple:
        return (
            RESOLUTION_SCORE.get(item.resolution, 1),
            item.seeders,
            item.size_bytes or 0,
        )

    return sorted(items, key=score, reverse=True)
