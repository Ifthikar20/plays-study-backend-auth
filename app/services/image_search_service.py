"""
Image search service using Unsplash API.
"""
import logging
import httpx
from typing import List, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class ImageSearchService:
    """Service for searching images using Unsplash API."""

    def __init__(self):
        self.access_key = settings.UNSPLASH_ACCESS_KEY
        self.base_url = "https://api.unsplash.com"

    def is_configured(self) -> bool:
        """Check if Unsplash API is configured."""
        return bool(self.access_key)

    async def search_images(
        self,
        query: str,
        per_page: int = 3,
        orientation: str = "landscape"
    ) -> List[Dict[str, str]]:
        """
        Search for images using Unsplash API.

        Args:
            query: Search query string
            per_page: Number of results to return (max 30)
            orientation: Image orientation (landscape, portrait, squarish)

        Returns:
            List of image dictionaries with url, thumb_url, description, and author
        """
        if not self.is_configured():
            logger.warning("[Image Search] Unsplash API not configured")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/search/photos",
                    params={
                        "query": query,
                        "per_page": min(per_page, 30),
                        "orientation": orientation,
                        "content_filter": "high",  # Family-friendly content
                    },
                    headers={
                        "Authorization": f"Client-ID {self.access_key}",
                    }
                )

                if response.status_code != 200:
                    logger.error(f"[Image Search] API error: {response.status_code} - {response.text}")
                    return []

                data = response.json()
                results = data.get("results", [])

                images = []
                for result in results:
                    images.append({
                        "url": result["urls"]["regular"],
                        "thumb_url": result["urls"]["small"],
                        "description": result.get("alt_description") or result.get("description") or query,
                        "author": result["user"]["name"],
                        "author_url": result["user"]["links"]["html"],
                        "unsplash_url": result["links"]["html"],
                    })

                logger.info(f"[Image Search] Found {len(images)} images for query: {query}")
                return images

        except httpx.TimeoutException:
            logger.error(f"[Image Search] Timeout searching for: {query}")
            return []
        except Exception as e:
            logger.error(f"[Image Search] Error: {str(e)}", exc_info=True)
            return []

    async def get_topic_image(self, topic_title: str, topic_description: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Get a single relevant image for a topic.

        Args:
            topic_title: The topic title
            topic_description: Optional topic description for better search

        Returns:
            Single image dictionary or None
        """
        # Construct search query
        search_query = topic_title
        if topic_description:
            # Extract key terms from description (first 50 chars)
            desc_terms = topic_description[:50].strip()
            search_query = f"{topic_title} {desc_terms}"

        images = await self.search_images(search_query, per_page=1)
        return images[0] if images else None


# Global instance
image_search_service = ImageSearchService()
