import os
import httpx
import gzip
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class CoomerScraper:
    BASE_API_URL = "https://coomer.st/api/v1"
    BASE_MEDIA_URL = "https://coomer.st/data"
    
    def __init__(self, user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"):
        self.headers = {
            "User-Agent": user_agent,
            "Referer": "https://coomer.st/",
            "Accept": "text/css",
        }
        self.client = httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=30.0)

    async def close(self):
        await self.client.aclose()

    def _parse_url(self, url: str) -> Optional[Dict[str, str]]:
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) >= 3 and parts[1] == "user":
            return {"service": parts[0], "user_id": parts[2]}
        return None

    async def fetch_posts(self, service: str, user_id: str, offset: int = 0) -> List[Dict[str, Any]]:
        url = f"{self.BASE_API_URL}/{service}/user/{user_id}/posts?o={offset}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            content = response.content
            if content.startswith(b'\x1f\x8b'):
                content = gzip.decompress(content)
            data = json.loads(content)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error fetching posts: {e}")
            return []

    async def get_all_videos(self, profile_url: str, limit: Optional[int] = None, start_offset: int = 0, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        info = self._parse_url(profile_url)
        if not info: return []
        all_videos = []
        offset = start_offset
        pages_fetched = 0
        while True:
            if max_pages is not None and pages_fetched >= max_pages: break
            posts = await self.fetch_posts(info["service"], info["user_id"], offset)
            if not posts: break
            for post in posts:
                for attr in post.get("attachments", []):
                    name, path = attr.get("name", ""), attr.get("path", "")
                    if name.lower().endswith((".mp4", ".m4v", ".mov")):
                        all_videos.append({
                            "post_id": post.get("id"),
                            "name": name,
                            "url": f"{self.BASE_MEDIA_URL}{path}",
                            "published": post.get("published"),
                            "description": post.get("substring", "")
                        })
                if limit is not None and len(all_videos) >= limit: return all_videos[:limit]
            offset += 50
            pages_fetched += 1
            if len(posts) < 50: break
        return all_videos

    async def download_video(self, url: str, output_path: str, semaphore: Optional[asyncio.Semaphore] = None, progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        async def _do_download() -> bool:
            try:
                async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=None) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)
                                if progress_callback: progress_callback(len(chunk))
                return True
            except Exception as e:
                logger.error(f"Download error: {e}")
                return False
        if semaphore:
            async with semaphore: return await _do_download()
        return await _do_download()
