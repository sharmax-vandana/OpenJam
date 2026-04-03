"""Music search service using iTunes Search API — zero API key required."""

import logging
import urllib.parse
import urllib.request
import json

logger = logging.getLogger(__name__)

ITUNES_API = "https://itunes.apple.com/search"


class MusicSearchService:
    """Search tracks via the Apple iTunes Search API (completely free, no key needed)."""

    def search_tracks(self, query: str, limit: int = 10) -> list:
        """Search iTunes for tracks. Returns list compatible with existing data shape."""
        if not query or not query.strip():
            return []

        params = urllib.parse.urlencode({
            "term": query.strip(),
            "media": "music",
            "entity": "song",
            "limit": min(limit, 25),
        })

        try:
            url = f"{ITUNES_API}?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "OpenJam/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            logger.error(f"iTunes API error for query '{query}': {e}")
            return []

        results = data.get("results", [])
        tracks = []
        for item in results[:limit]:
            if item.get("kind") != "song":
                continue

            name = item.get("trackName", "Unknown")
            artist = item.get("artistName", "Unknown")

            # iTunes gives 100x100 artwork — bump to 600x600 for quality
            artwork = (item.get("artworkUrl100") or "").replace("100x100bb", "600x600bb")

            duration_ms = item.get("trackTimeMillis") or 0

            # uri = YouTube search query string — frontend resolves to video ID
            youtube_query = f"{name} {artist} official audio"

            tracks.append({
                "uri": youtube_query,
                "name": name,
                "artist": artist,
                "album_art_url": artwork or None,
                "duration_ms": duration_ms,
            })

        logger.debug(f"iTunes search '{query}' → {len(tracks)} results")
        return tracks


# Keep import alias so nothing else needs to change
lastfm_service = MusicSearchService()
