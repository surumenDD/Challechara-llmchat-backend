from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


from models.schemas import (
    ChatRequest, 
    ChatResponse, 
    ChatMessage
)
from services.gemini_service import get_gemini_service, GeminiChatService

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat/project", response_model=ChatResponse)
async def project_chat(
    request: ChatRequest,
    gemini_service: GeminiChatService = Depends(get_gemini_service)
):
    """プロジェクトファイルを参照したチャット"""
    try:
        logger.info(f"Project chat request with {len(request.messages)} messages")
        logger.info(f"Sources: {request.sources}")
        
        response_message = await gemini_service.generate_response(
            request, 
            chat_type="project"
        )
        
        return ChatResponse(
            message=response_message,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error in project chat: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "project_chat_error",
                "message": "プロジェクトチャットでエラーが発生しました",
                "details": str(e)
            }
        )

@router.post("/chat/dictionary", response_model=ChatResponse)
async def dictionary_chat(
    request: ChatRequest,
    gemini_service: GeminiChatService = Depends(get_gemini_service)
):
    """辞書・表現検索チャット"""
    try:
        logger.info(f"Dictionary chat request with {len(request.messages)} messages")
        
        response_message = await gemini_service.generate_response(
            request, 
            chat_type="dictionary"
        )
        
        return ChatResponse(
            message=response_message,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error in dictionary chat: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "dictionary_chat_error",
                "message": "辞書チャットでエラーが発生しました",
                "details": str(e)
            }
        )

GO_MATERIAL_API_URL = "http://localhost:8080/api/materials/batch"

async def fetch_materials_by_ids(ids: list[int]):
    """Go APIから複数マテリアルをID指定で取得"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                GO_MATERIAL_API_URL,
                json={"ids": ids},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            materials = response.json()
            return materials
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching materials: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch materials from Go API")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while fetching materials: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Go API returned error")


@router.post("/chat/material", response_model=ChatResponse)
async def material_chat(
    request: ChatRequest,
    gemini_service: GeminiChatService = Depends(get_gemini_service)
):
    """資料を参照したチャット"""
    try:
        logger.info(f"Material chat request with {len(request.messages)} messages")
        logger.info(f"Sources: {request.sources}")
        
        response_message = await gemini_service.generate_response(
            request, 
            chat_type="material"
        )
        
        return ChatResponse(
            message=response_message,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error in material chat: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "material_chat_error",
                "message": "資料チャットでエラーが発生しました",
                "details": str(e)
            }
        )