from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import os

from routers import chat, dictionary, materials

# 環境変数を読み込み
load_dotenv()

app = FastAPI(
    title="Challechara Backend API",
    description="作家支援アプリケーション用のバックエンドAPI",
    version="1.0.0"
)

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.jsのデフォルトポート
        "http://127.0.0.1:3000",
        "https://your-frontend-domain.com"  # 本番環境のドメインを追加
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ルーターを登録
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(dictionary.router, prefix="/api", tags=["dictionary"])
app.include_router(materials.router, prefix="/api", tags=["materials"])

@app.get("/")
async def root():
    return {"message": "Challechara Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "message": "API is running"}

# グローバル例外ハンドラー
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "予期しないエラーが発生しました。しばらくお待ちいただいてから再度お試しください。",
            "details": str(exc) if os.getenv("DEBUG") else None
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True if os.getenv("DEBUG") else False
    )