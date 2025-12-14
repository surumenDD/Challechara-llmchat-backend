"""
GoのAPIからデータを取得してLLMに渡すサービス
"""
import os
import logging
import httpx
import html
import re
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
    
    async def get_episodes_by_ids(self, book_id: str, episode_ids: List[str]) -> List[Dict]:
        """複数のエピソードIDから一括取得（POST /api/books/{book_id}/episodes/batch）"""
        if not episode_ids:
            logger.warning("⚠️ No episode IDs provided")
            return []
        
        url = f"{self.base_url}/api/books/{book_id}/episodes/batch"
        payload = {"ids": episode_ids}
        
        try:
            logger.info(f"📖 [Go API] POST {url}")
            logger.info(f"📖 [Go API] Request body: {payload}")
            logger.info(f"📖 Fetching {len(episode_ids)} episodes for book {book_id}")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                episodes = response.json()
                logger.info(f"✅ [Go API] Received {len(episodes)} episodes")
                return episodes
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return []
    
    # ========== Material API ==========
    
    async def get_materials_by_ids(self, book_id: str, material_ids: List[str]) -> List[Dict]:
        """複数の資料IDから一括取得（POST /api/books/{book_id}/materials/batch）"""
        if not material_ids:
            logger.warning("⚠️ No material IDs provided")
            return []
        
        url = f"{self.base_url}/api/books/{book_id}/materials/batch"
        payload = {"ids": material_ids}
        
        try:
            logger.info(f"📚 [Go API] POST {url}")
            logger.info(f"📚 [Go API] Request body: {payload}")
            logger.info(f"📚 Fetching {len(material_ids)} materials for book {book_id}")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                materials = response.json()
                logger.info(f"✅ [Go API] Received {len(materials)} materials")
                return materials
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return []


def _clean_html_content(content: str) -> str:
    """HTMLタグを除去してプレーンテキストに変換"""
    if not content:
        return ""
    
    # HTMLエスケープを解除
    content = html.unescape(content)
    
    # <br> を改行に変換
    content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
    
    # <p>タグを改行に変換
    content = re.sub(r'</p>', '\n\n', content, flags=re.IGNORECASE)
    content = re.sub(r'<p[^>]*>', '', content, flags=re.IGNORECASE)
    
    # 残りのHTMLタグを全削除
    content = re.sub(r'<[^>]+>', '', content)
    
    # 連続する空白・改行を整理
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    
    return content.strip()


def format_episodes_for_context(episodes: List[Dict], max_length: int = 5000) -> str:
    """エピソードをLLMコンテキスト用にフォーマット"""
    if not episodes:
        return ""
    
    formatted = ["=== 参照エピソード ==="]
    
    for episode in episodes:
        episode_no = episode.get('episode_no', '?')
        title = episode.get('title', '無題')
        content = episode.get('content', '')
        
        # HTMLタグを除去
        content = _clean_html_content(content)
        
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
        
        # HTMLタグを除去
        content = _clean_html_content(content)
        
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
