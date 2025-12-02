"""
GoのAPIからデータを取得してLLMに渡すサービス
"""
import os
import logging
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class GoAPIClient:
    """GoバックエンドAPIクライアント"""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            base_url = os.getenv("GO_API_URL", "http://localhost:8080")
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(30.0)
    
    # ========== Episode API ==========
    
    async def get_episodes(self, book_id: str) -> List[Dict]:
        """特定のbookのエピソード一覧を取得"""
        url = f"{self.base_url}/api/books/{book_id}/episodes"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                episodes = response.json()
                logger.info(f"✅ Fetched {len(episodes)} episodes for book {book_id}")
                return episodes
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Book {book_id} not found")
                return []
            logger.error(f"HTTP error fetching episodes: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching episodes from Go API: {e}")
            raise
    
    async def get_episode(self, episode_id: int) -> Optional[Dict]:
        """特定のエピソードを取得"""
        url = f"{self.base_url}/api/episodes/{episode_id}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                episode = response.json()
                logger.info(f"✅ Fetched episode {episode_id}")
                return episode
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Episode {episode_id} not found")
                return None
            logger.error(f"HTTP error fetching episode: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching episode from Go API: {e}")
            raise
    
    # ========== Material API ==========
    
    async def get_materials(self, book_id: str) -> List[Dict]:
        """特定のbookの参考資料一覧を取得"""
        url = f"{self.base_url}/api/books/{book_id}/materials"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                materials = response.json()
                logger.info(f"✅ Fetched {len(materials)} materials for book {book_id}")
                return materials
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Book {book_id} not found for materials")
                return []
            logger.error(f"HTTP error fetching materials: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching materials from Go API: {e}")
            raise
    
    async def get_material(self, material_id: int) -> Optional[Dict]:
        """特定の参考資料を取得"""
        url = f"{self.base_url}/api/materials/{material_id}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                material = response.json()
                logger.info(f"✅ Fetched material {material_id}")
                return material
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Material {material_id} not found")
                return None
            logger.error(f"HTTP error fetching material: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching material from Go API: {e}")
            raise


def format_episodes_for_context(episodes: List[Dict], max_length: int = 5000) -> str:
    """エピソードをLLMコンテキスト用にフォーマット"""
    if not episodes:
        return ""
    
    formatted = ["=== 参照エピソード ==="]
    
    for episode in episodes:
        episode_no = episode.get('episode_no', '?')
        title = episode.get('title', '無題')
        content = episode.get('content', '')
        
        formatted.append(f"\n--- Episode {episode_no}: {title} ---")
        
        if len(content) > max_length:
            formatted.append(content[:max_length] + f"\n... (残り{len(content) - max_length}文字省略)")
        else:
            formatted.append(content)
        
        formatted.append("--- エピソード終了 ---")
    
    formatted.append("=== 参照エピソード終了 ===\n")
    return "\n".join(formatted)


def format_materials_for_context(materials: List[Dict], max_length: int = 5000) -> str:
    """参考資料をLLMコンテキスト用にフォーマット"""
    if not materials:
        return ""
    
    formatted = ["=== 参考資料 ==="]
    
    for material in materials:
        title = material.get('title', '無題')
        content = material.get('content', '')
        created_at = material.get('created_at', '')
        
        formatted.append(f"\n--- 資料: {title} ({created_at}) ---")
        
        if len(content) > max_length:
            formatted.append(content[:max_length] + f"\n... (残り{len(content) - max_length}文字省略)")
        else:
            formatted.append(content)
        
        formatted.append("--- 資料終了 ---")
    
    formatted.append("=== 参考資料終了 ===\n")
    return "\n".join(formatted)


# シングルトンインスタンス
_go_api_client = None


def get_go_api_client() -> GoAPIClient:
    """GoAPIClientのシングルトンインスタンスを取得"""
    global _go_api_client
    if _go_api_client is None:
        _go_api_client = GoAPIClient()
    return _go_api_client
