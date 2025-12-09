import google.generativeai as genai
from typing import List, Optional
import os
import logging
from models.schemas import ChatMessage, ChatRequest
from services.go_api_client import get_go_api_client, format_episodes_for_context, format_materials_for_context

# ログ設定
logger = logging.getLogger(__name__)


class GeminiChatService:
    """Gemini APIを使用したチャットサービス"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        # GoAPIクライアントを取得
        self.go_api_client = get_go_api_client()

        # 作家向けシステムプロンプト
        self.system_prompts = {
            "project": """
あなたは作家の執筆をサポートするAIアシスタントです。
提供されたプロジェクト（執筆中のエピソード）の内容を参考にして、執筆に役立つ回答をしてください。
- ストーリーの一貫性を保つためのアドバイス
- キャラクター設定の確認
- プロットの展開に関する提案
- 文章の改善提案
- 既存の文章との整合性チェック
などを行ってください。プロジェクトファイルの内容をしっかりと参照して回答してください。
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
提供された参考資料の内容を分析し、執筆に役立つ情報を提供してください。
- 重要なポイントの抽出
- 関連情報の補足
- 創作への応用方法
- 背景知識の説明
- 資料間の関連性の指摘
などを行ってください。提供された資料の内容をしっかりと参照して回答してください。
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

            # GoAPIからデータを取得してコンテキストに追加
            content_context = ""
            content_not_found = []
            
            if chat_type == "project" and request.sources:
                # プロジェクト(episodes)を取得
                for source in request.sources:
                    # sourceの形式: "project:book_id:episode_id1,episode_id2,..." または "book:book_id"
                    if source.startswith("project:") or source.startswith("book:"):
                        parts = source.split(":")
                        if len(parts) >= 3:
                            # project:book_id:episode_ids の形式
                            book_id = parts[1]
                            episode_ids = parts[2].split(",") if parts[2] else []
                            
                            logger.info(f"📖 [プロジェクト] Fetching {len(episode_ids)} episodes for book: {book_id}")
                            try:
                                episodes = await self.go_api_client.get_episodes_by_ids(book_id, episode_ids)
                                
                                if episodes:
                                    content_context += format_episodes_for_context(episodes)
                                    logger.info(f"✅ [プロジェクト] {len(episodes)} episodes loaded")
                                else:
                                    logger.warning(f"⚠️ [プロジェクト] No episodes found for IDs: {episode_ids}")
                                    content_not_found.append(f"project:{book_id}")
                            except Exception as e:
                                logger.error(f"❌ [プロジェクト] Error fetching episodes: {e}")
                                content_not_found.append(f"project:{book_id}")
                        elif len(parts) >= 2:
                            # book:book_id の形式（後方互換）
                            book_id = parts[1]
                            logger.warning(f"⚠️ [プロジェクト] Legacy format 'book:{book_id}' - no episode IDs provided")
                            content_not_found.append(f"book:{book_id}")
            
            elif chat_type == "material" and request.sources:
                # 参考資料(materials)を取得
                logger.info(f"🔍 [資料] Processing sources: {request.sources}")
                for source in request.sources:
                    logger.info(f"🔍 [資料] Processing source: {source}")
                    # sourceの形式: "material:book_id:material_id1,material_id2,..." または "book:book_id"
                    if source.startswith("material:") or source.startswith("book:"):
                        parts = source.split(":")
                        logger.info(f"🔍 [資料] Split parts: {parts}, length: {len(parts)}")
                        if len(parts) >= 3:
                            # material:book_id:material_ids の形式
                            book_id = parts[1]
                            material_ids = parts[2].split(",") if parts[2] else []
                            
                            logger.info(f"📚 [資料] Fetching {len(material_ids)} materials for book: {book_id}")
                            try:
                                materials = await self.go_api_client.get_materials_by_ids(book_id, material_ids)
                                
                                if materials:
                                    content_context += format_materials_for_context(materials)
                                    logger.info(f"✅ [資料] {len(materials)} materials loaded")
                                else:
                                    logger.warning(f"⚠️ [資料] No materials found for IDs: {material_ids}")
                                    content_not_found.append(f"material:{book_id}")
                            except Exception as e:
                                logger.error(f"❌ [資料] Error fetching materials: {e}")
                                content_not_found.append(f"material:{book_id}")
                        elif len(parts) >= 2:
                            # book:book_id の形式（後方互換）
                            book_id = parts[1]
                            logger.warning(f"⚠️ [資料] Legacy format 'book:{book_id}' - no material IDs provided")
                            content_not_found.append(f"book:{book_id}")

            # コンテキストを追加
            if content_context:
                conversation_history.append(content_context)
            elif content_not_found:
                # データが見つからない場合の対応
                data_type_ja = "プロジェクト" if chat_type == "project" else "参考資料"
                logger.error(f"❌ {data_type_ja}が見つかりません: {content_not_found}")
                import time
                return ChatMessage(
                    id=f"error-{int(time.time())}",
                    role="assistant", 
                    content=f"申し訳ございません。指定された{data_type_ja}（{', '.join(content_not_found)}）が見つかりません。\n\n{data_type_ja}が正しく登録されているか確認してください。",
                    ts=int(time.time() * 1000)
                )

            # ソース情報を追加（レガシー対応）
            if request.sources and not content_context and not content_not_found:
                source_info = f"参照するソース: {', '.join(request.sources)}"
                conversation_history.append(source_info)

            # 会話履歴を追加
            for msg in request.messages:
                role = "ユーザー" if msg.role == "user" else "アシスタント"
                conversation_history.append(f"{role}: {msg.content}")

            # プロンプトを結合
            prompt = "\n".join(conversation_history)

            # デバッグログ（プロンプトが長すぎる場合は省略）
            if len(prompt) > 1000:
                logger.info(
                    f"Generated prompt length: {len(prompt)} characters")
            else:
                logger.info(f"Generated prompt: {prompt}")

            # Gemini APIを呼び出し
            logger.info(f"Generating response for chat_type: {chat_type}")

            # プロンプトが長すぎる場合は短縮
            if len(prompt) > 30000:  # 30KB制限
                logger.warning(
                    f"Prompt too long ({len(prompt)} chars), truncating...")
                prompt = prompt[:30000] + "\n\n[プロンプトが長いため省略されました]"

            # Gemini API設定とタイムアウト対策
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000,  # 出力トークン数を増やす
            )

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=False
            )

            # レスポンスの検証
            response_text = ""
            
            if response.candidates:
                # 候補がある場合、最初の候補からテキストを取得
                candidate = response.candidates[0]
                
                if candidate.content and candidate.content.parts:
                    # 全てのパートからテキストを抽出
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    response_text = "".join(text_parts)
                    
                    # MAX_TOKENSで切り捨てられた場合のログ
                    if candidate.finish_reason == 2:  # MAX_TOKENS
                        logger.warning("Response was truncated due to max_tokens limit")
                elif candidate.finish_reason == 2:
                    # finish_reasonがMAX_TOKENSの場合、部分的でもcontentがあれば取得を試行
                    try:
                        if candidate.content and hasattr(candidate.content, 'parts'):
                            text_parts = []
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    text_parts.append(str(part.text) if part.text else "")
                            response_text = "".join(text_parts)
                    except Exception as extract_error:
                        logger.error(f"Error extracting partial response: {extract_error}")
                        
                if not response_text.strip():
                    logger.warning("Response candidate has no content or parts")
                    response_text = "申し訳ございません。AIからの応答が空でした。"
            else:
                logger.warning("No candidates in response")
                response_text = "申し訳ございません。AIから有効な応答が得られませんでした。"

            # 空のレスポンスの場合のフォールバック
            if not response_text.strip():
                logger.warning("Empty response text received")
                data_type_ja = "プロジェクト" if chat_type == "project" else "参考資料" if chat_type == "material" else "データ"
                if content_context:
                    response_text = f"申し訳ございません。{data_type_ja}の内容を参照しましたが、適切な応答を生成できませんでした。質問を具体的にしていただくか、別の表現でお試しください。"
                else:
                    response_text = f"申し訳ございません。参照する{data_type_ja}が見つからないか、内容が不十分で適切な応答を生成できませんでした。{data_type_ja}を確認してから再度お試しください。"

            # レスポンスメッセージを作成
            import time
            return ChatMessage(
                id=f"msg-{int(time.time())}-{abs(hash(response_text)) % 10000}",
                role="assistant",
                content=response_text,
                ts=int(time.time() * 1000)
            )

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error generating response: {error_message}")

            # エラーの種類に応じてより具体的なメッセージを返す
            if "504" in error_message or "timeout" in error_message.lower():
                content = "サーバーの応答に時間がかかっています。プロンプトを短くして再度お試しください。"
            elif "API_KEY" in error_message:
                content = "API設定に問題があります。管理者にお問い合わせください。"
            elif "quota" in error_message.lower() or "limit" in error_message.lower():
                content = "API利用制限に達しています。しばらくお待ちください。"
            else:
                content = f"申し訳ございません。エラーが発生しました: {error_message[:100]}"

            # エラー時のフォールバック
            import time
            return ChatMessage(
                id=f"error-{int(time.time())}",
                role="assistant",
                content=content,
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
            
            # レスポンスの検証
            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    response_text = "".join(text_parts)
                else:
                    response_text = f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"
            else:
                response_text = f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"
            
            return response_text if response_text.strip() else f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"

        except Exception as e:
            logger.error(f"Error in dictionary search: {e}")
            return f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"


# シングルトンインスタンス
_gemini_service = None


def get_gemini_service() -> GeminiChatService:
    """Geminiサービスのシングルトンインスタンスを取得"""
    global _gemini_service
    if _gemini_service is None:
        import os
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        _gemini_service = GeminiChatService(api_key=api_key)
    return _gemini_service
