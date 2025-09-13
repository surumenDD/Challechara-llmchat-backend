import google.generativeai as genai
from typing import List, Optional
import os
import logging
from models.schemas import ChatMessage, ChatRequest

# ログ設定
logger = logging.getLogger(__name__)

class GeminiChatService:
    """Gemini APIを使用したチャットサービス"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Gemini APIを設定
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 作家向けシステムプロンプト
        self.system_prompts = {
            "project": """
あなたは作家の執筆をサポートするAIアシスタントです。
提供されたプロジェクトファイルの内容を参考にして、執筆に役立つ回答をしてください。
- ストーリーの一貫性を保つためのアドバイス
- キャラクター設定の確認
- プロットの展開に関する提案
- 文章の改善提案
などを行ってください。
""",
            "dictionary": """
あなたは作家向けの表現・言語アシスタントです。
- 適切な言葉選び
- 表現の豊かさ
- 語彙の提案
- 文章の推敲
- 表現技法のアドバイス
などを提供してください。文学的で美しい表現を心がけてください。
""",
            "material": """
あなたは資料研究をサポートするAIアシスタントです。
提供された資料の内容を分析し、執筆に役立つ情報を提供してください。
- 重要なポイントの抽出
- 関連情報の補足
- 創作への応用方法
- 背景知識の説明
などを行ってください。
"""
        }

    async def generate_response(
        self, 
        request: ChatRequest, 
        chat_type: str = "general"
    ) -> ChatMessage:
        """チャットレスポンスを生成"""
        try:
            # システムプロンプトを取得
            system_prompt = self.system_prompts.get(chat_type, "")
            
            # 会話履歴を構築
            conversation_history = []
            
            # システムプロンプトを追加
            if system_prompt:
                conversation_history.append(f"システム: {system_prompt}")
            
            # ソース情報を追加
            if request.sources:
                source_info = f"参照するソース: {', '.join(request.sources)}"
                conversation_history.append(source_info)
            
            # 会話履歴を追加
            for msg in request.messages:
                role = "ユーザー" if msg.role == "user" else "アシスタント"
                conversation_history.append(f"{role}: {msg.content}")
            
            # プロンプトを結合
            prompt = "\n".join(conversation_history)
            
            # Gemini APIを呼び出し
            logger.info(f"Generating response for chat_type: {chat_type}")
            response = self.model.generate_content(prompt)
            
            # レスポンスメッセージを作成
            import time
            return ChatMessage(
                id=f"msg-{int(time.time())}-{hash(response.text) % 10000}",
                role="assistant",
                content=response.text,
                ts=int(time.time() * 1000)
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # エラー時のフォールバック
            import time
            return ChatMessage(
                id=f"error-{int(time.time())}",
                role="assistant",
                content="申し訳ございません。現在、一時的にサービスに接続できません。しばらくお待ちいただいてから、再度お試しください。",
                ts=int(time.time() * 1000)
            )

    async def search_dictionary(self, query: str) -> str:
        """辞書検索機能（Geminiを使用して詳細な解説を生成）"""
        try:
            prompt = f"""
以下の単語・表現について、作家向けの詳細な解説をしてください：
「{query}」

以下の情報を含めてください：
1. 基本的な意味・定義
2. 語源や成り立ち（分かる場合）
3. 使用例・用例
4. 類語・類似表現
5. 文学作品での使用例（あれば）
6. 作家としての効果的な使い方のアドバイス

詳しく、分かりやすく説明してください。
"""
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error in dictionary search: {e}")
            return f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"

# シングルトンインスタンス
_gemini_service = None

def get_gemini_service() -> GeminiChatService:
    """Geminiサービスのシングルトンインスタンスを取得"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiChatService()
    return _gemini_service