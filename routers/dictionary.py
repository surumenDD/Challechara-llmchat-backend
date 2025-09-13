from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import logging

from models.schemas import DictionarySearchRequest, DictionarySearchResponse, DictionaryEntry
from services.gemini_service import get_gemini_service, GeminiChatService

logger = logging.getLogger(__name__)

router = APIRouter()

# ダミー辞書データ（実際の辞書APIがない場合の代替）
DUMMY_DICTIONARY = [
    {
        "id": "1",
        "word": "美しい",
        "reading": "うつくしい",
        "part_of_speech": "形容詞",
        "meanings": ["形や色などが整っていて、見て快く感じるさま"],
        "examples": ["美しい景色", "美しい音楽"],
        "synonyms": ["麗しい", "綺麗な", "素晴らしい"]
    },
    {
        "id": "2",
        "word": "静謐",
        "reading": "せいひつ",
        "part_of_speech": "名詞・形容動詞",
        "meanings": ["静かで落ち着いているさま"],
        "examples": ["静謐な空間", "静謐な午後"],
        "synonyms": ["静寂", "平穏", "閑静"]
    },
    {
        "id": "3",
        "word": "幽玄",
        "reading": "ゆうげん",
        "part_of_speech": "名詞・形容動詞",
        "meanings": ["奥深くて上品なさま", "神秘的で深遠なさま"],
        "examples": ["幽玄な美", "幽玄な世界"],
        "synonyms": ["神秘的", "奥深い", "上品"]
    },
    {
        "id": "4",
        "word": "風雅",
        "reading": "ふうが",
        "part_of_speech": "名詞・形容動詞",
        "meanings": ["上品で洗練されたさま", "風流で雅やかなさま"],
        "examples": ["風雅な趣味", "風雅な生活"],
        "synonyms": ["風流", "雅やか", "上品"]
    },
    {
        "id": "5",
        "word": "侘寂",
        "reading": "わびさび",
        "part_of_speech": "名詞",
        "meanings": ["不完全さや無常性の中に見出す美意識"],
        "examples": ["侘寂の美学", "侘寂な庭園"],
        "synonyms": ["わび", "さび", "枯淡"]
    }
]

@router.get("/dictionary/search", response_model=DictionarySearchResponse)
async def search_dictionary(
    query: str = Query(..., description="検索する単語・表現"),
    limit: int = Query(10, ge=1, le=50, description="取得する結果数"),
    gemini_service: GeminiChatService = Depends(get_gemini_service)
):
    """辞書・表現検索"""
    try:
        logger.info(f"Dictionary search query: {query}")
        
        # ダミーデータから検索
        filtered_results = []
        for entry_data in DUMMY_DICTIONARY:
            if (query.lower() in entry_data["word"].lower() or 
                query.lower() in entry_data["reading"].lower() or
                any(query.lower() in meaning.lower() for meaning in entry_data["meanings"])):
                
                entry = DictionaryEntry(**entry_data)
                filtered_results.append(entry)
        
        # 結果が見つからない場合、Geminiで動的に検索結果を生成
        if not filtered_results:
            logger.info(f"No dictionary results found, using Gemini for: {query}")
            
            try:
                gemini_explanation = await gemini_service.search_dictionary(query)
                
                # Geminiの結果から辞書エントリを生成
                dynamic_entry = DictionaryEntry(
                    id=f"gemini-{abs(hash(query)) % 10000}",
                    word=query,
                    reading="※読み方調査中",
                    part_of_speech="※品詞調査中",
                    meanings=[gemini_explanation],
                    examples=["※用例調査中"],
                    synonyms=["※類語調査中"]
                )
                filtered_results.append(dynamic_entry)
                
            except Exception as e:
                logger.error(f"Error generating dynamic dictionary entry: {e}")
                # Geminiでもエラーが発生した場合のフォールバック
                fallback_entry = DictionaryEntry(
                    id=f"fallback-{abs(hash(query)) % 10000}",
                    word=query,
                    reading="※調査中",
                    part_of_speech="※調査中",
                    meanings=[f"「{query}」について情報を収集中です。しばらくお待ちください。"],
                    examples=["※例文準備中"],
                    synonyms=["※類語調査中"]
                )
                filtered_results.append(fallback_entry)
        
        # 結果を制限
        limited_results = filtered_results[:limit]
        
        return DictionarySearchResponse(
            results=limited_results,
            total=len(filtered_results),
            query=query
        )
        
    except Exception as e:
        logger.error(f"Error in dictionary search: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "dictionary_search_error",
                "message": "辞書検索でエラーが発生しました",
                "details": str(e)
            }
        )

@router.get("/dictionary/suggest")
async def suggest_expressions(
    context: str = Query(..., description="文脈・コンテキスト"),
    gemini_service: GeminiChatService = Depends(get_gemini_service)
):
    """文脈に基づく表現提案"""
    try:
        logger.info(f"Expression suggestion for context: {context}")
        
        prompt = f"""
以下の文脈に適した表現・言い回しを提案してください：
「{context}」

以下の観点から、複数の表現を提案してください：
1. より文学的・美しい表現
2. より具体的・鮮明な表現  
3. より簡潔・明確な表現
4. より感情的・情緒的な表現

それぞれ3つずつ提案し、使用場面も説明してください。
"""
        
        response = await gemini_service.model.generate_content(prompt)
        
        return {
            "context": context,
            "suggestions": response.text,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in expression suggestion: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "expression_suggestion_error", 
                "message": "表現提案でエラーが発生しました",
                "details": str(e)
            }
        )