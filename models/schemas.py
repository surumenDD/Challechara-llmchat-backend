from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime


class ChatMessage(BaseModel):
    """チャットメッセージのモデル"""
    id: Optional[str] = None
    role: Literal["user", "assistant"]
    content: str
    ts: Optional[int] = None


class ChatRequest(BaseModel):
    """チャットリクエストのモデル"""
    messages: List[ChatMessage]
    sources: Optional[List[str]] = []  # "project:book_id:ep1,ep2" or "material:book_id:mat1,mat2"
    context: Optional[str] = None


class ChatResponse(BaseModel):
    """チャットレスポンスのモデル"""
    message: ChatMessage
    success: bool
    error: Optional[str] = None


class ProjectFile(BaseModel):
    """プロジェクトファイルのモデル"""
    id: str
    title: str
    content: str
    created_at: int
    updated_at: int


class Material(BaseModel):
    """資料のモデル"""
    id: str
    title: str
    content: str
    file_type: Optional[str] = None
    size: Optional[int] = None
    created_at: int


class DictionaryEntry(BaseModel):
    """辞書エントリのモデル"""
    id: str
    word: str
    reading: str
    part_of_speech: str
    meanings: List[str]
    examples: List[str]
    synonyms: List[str]


class DictionarySearchRequest(BaseModel):
    """辞書検索リクエストのモデル"""
    query: str
    limit: Optional[int] = 10


class DictionarySearchResponse(BaseModel):
    """辞書検索レスポンスのモデル"""
    results: List[DictionaryEntry]
    total: int
    query: str


class MaterialUploadRequest(BaseModel):
    """資料アップロードリクエストのモデル"""
    book_id: str
    title: str
    content: str
    file_type: Optional[str] = None


class ErrorResponse(BaseModel):
    """エラーレスポンスのモデル"""
    error: str
    message: str
    details: Optional[str] = None
