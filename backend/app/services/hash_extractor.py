import re
from urllib.parse import parse_qs, unquote, urlparse


HEX_40_RE = re.compile(r"\b[a-fA-F0-9]{40}\b")


def extract_infohash(magnet_or_text: str) -> str | None:
    if not magnet_or_text:
        return None

    if magnet_or_text.startswith("magnet:?"):
        parsed = urlparse(magnet_or_text)
        params = parse_qs(parsed.query)
        xt_values = params.get("xt", [])
        for xt in xt_values:
            if xt.startswith("urn:btih:"):
                raw = unquote(xt.replace("urn:btih:", "").strip())
                match = HEX_40_RE.search(raw)
                if match:
                    return match.group(0).lower()

    match = HEX_40_RE.search(magnet_or_text)
    if match:
        return match.group(0).lower()

    return None


def infer_resolution(text: str) -> str | None:
    lowered = text.lower()
    for token in ["2160p", "4k", "1080p", "720p", "480p"]:
        if token in lowered:
            return "2160p" if token == "4k" else token
    return None
