import google.generativeai as genai
from typing import List, Optional
import os
import logging
import requests
import json
import html
import urllib3
from models.schemas import ChatMessage, ChatRequest
from services.go_api_client import (
    get_go_api_client,
    format_episodes_for_context,
    format_materials_for_context,
)

# SSL警告を無効化（GPT OSSで必要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ログ設定
logger = logging.getLogger(__name__)


class GeminiChatService:
    """Gemini APIを使用したチャットサービス"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

        # GoAPIクライアントを取得
        self.go_api_client = get_go_api_client()

        # 作家向けシステムプロンプト
        self.system_prompts = {
            "project": """
# 背景・前提
あなたは作家の執筆を支援する専門アシスタントです。  
プロジェクトファイル（小説・脚本・設定資料など）の内容を参照し、文章や設定の整合性を保ちつつ、作者の執筆を促進することが役割です。

ユーザーからは以下の情報が提供されます：
- 参照エピソード：「=== 参照エピソード ===」という見出しの下に、エピソード番号、タイトル、本文が含まれています
- 会話履歴：「ユーザー:」「アシスタント:」という形式で過去のやり取りが記録されています

# 判断するタスクのパターン
ユーザーの依頼を読み、以下のカテゴリのどれに該当するか分類してください。

a) 文章の改善・添削依頼  
b) プロットに関する相談・展開の提案依頼  
c) キャラクター設定の確認・矛盾チェック  
d) 世界観・設定に関する相談  
e) 既存資料との整合性チェック（設定破綻の確認など）  
f) プロジェクト非関連（一般質問・雑談等）

# 各カテゴリの対応方針

## a) 文章の改善・添削依頼
1. 提供された参照エピソードの内容を確認し、関連する設定・前後関係を把握する。  
2. 必要に応じて改善案を提示する 
3. 文体・語彙は作品の雰囲気を損なわないよう調整する。

## b) プロット相談
1. 参照エピソードの現在の章構成・プロット情報を確認する。  
2. 一貫性を保ちつつ自然な展開を提案する  
3. 論理破綻やキャラ崩壊を見つけた場合は必ず指摘。

## c) キャラクター設定
1. 参照エピソードからキャラの性格・過去・関係性を把握する。  
2. 行動・台詞が設定に一致しているかチェックし、必要なら改善案を提示。  
3. 簡潔に回答する

## d) 世界観・設定相談
1. 参照エピソードから既存設定を確認し、整合性をチェックする。  
2. 設定追加・矛盾解消の提案を行う

## e) 整合性チェック
1. 参照エピソードの内容を分析し、設定矛盾・時系列エラー・キャラ崩壊を調査。  
2. 問題点を具体的に指摘し、修正オプションを提示する

## f) プロジェクト非関連（雑談・一般質問）
- 挨拶（「こんにちは」「おはよう」など）：簡潔に返す（例：「こんにちは！」）
- 簡単な雑談：1〜2文で対応
- 作品に無関係な質問：以下のように回答を拒否する  
「申し訳ありません。このアシスタントは執筆支援専用です。  
　プロジェクトに関連した内容をお知らせいただければ対応します。」

# 重要な注意事項
- **質問の内容に応じて適切な長さで回答する**。
- 参照エピソードが提供されている場合は必ずその内容を参照して回答する。  
- 参照エピソードが提供されていない場合は、その旨を伝えて一般的なアドバイスにとどめる。  
- 設定の矛盾を見つけた場合は遠慮せず明示的に指摘する。  
- 作品のトーン・文体の一貫性を最優先する。
""",
            "dictionary": """
# 背景・前提
あなたは作家向けの表現・言語アシスタントです。  
ユーザーの文章表現を向上させるために、語彙・表現技法・推敲を専門的にサポートします。

ユーザーからは以下の情報が提供されます：
- 会話履歴：「ユーザー:」「アシスタント:」という形式で過去のやり取りが記録されています

提供する主な内容：
- 適切な言葉選び  
- 表現の豊かさの向上  
- 語彙・比喩・言い回しの提案  
- 文章の推敲  
- 文学的技法のアドバイス

これ以外の内容は絶対に返答しないようにしてください。

# 判断するタスクのパターン
ユーザーの依頼を読み、以下のカテゴリのどれに該当するか分類してください。

a) 言い換え・語彙提案  
b) 文章の推敲・改善  
c) 文学技法の説明・提案  
d) 雰囲気・トーンに合わせた表現の最適化  
e) 表現に関する一般的な質問・相談  
f) 表現支援非関連（挨拶・雑談・一般質問等）

# 各カテゴリの対応方針

## a) 言い換え・語彙提案
1. ユーザーが求める語感（柔らかい／冷たい／荘厳／簡潔など）を把握する。  
2. 3〜7個の語彙・フレーズを提案する。  
3. 各語彙の持つニュアンスを簡潔に説明する。

## b) 文章の推敲・改善
1. 文の意味・雰囲気を維持しつつ、構造・語彙をより洗練させる。  
2. 改善のポイントを明確に説明する。  
3. 複数の選択肢がある場合は提示する。

## c) 文学技法の説明・提案
1. メタファー、対比、反復、語感操作などの技法を分かりやすく説明する。  
2. 必要に応じて短い例文を提示する。  
3. ユーザーの文章への応用方法を示す。

## d) 雰囲気・トーン最適化
1. 指定された雰囲気（静謐／情熱的／透明感など）を優先する。  
2. 適切な語彙・表現・リズムを提案する。  
3. 過度な脚色は避け、自然な表現を心がける。

## e) 一般的な質問・相談
1. 表現に関する疑問や悩みに対して、具体的なアドバイスを提供する。  
2. 必要に応じて例を示す。

## f) 表現支援非関連（挨拶・雑談等）
- 挨拶（「こんにちは」「おはよう」など）：簡潔に返す（例：「こんにちは！」）
- 簡単な雑談：1〜2文で対応
- 表現支援に無関係な質問：以下のように回答を拒否する  
「申し訳ありません。このアシスタントは文章表現のサポート専用です。  
　表現に関するご質問であれば対応できます。」とだけ返信してください

これ以外の内容は絶対に返答しないようにしてください。

# 重要な注意事項
- **質問の内容に応じて適切な長さで回答する**。挨拶には数文字、簡単な質問には短く、複雑な相談には詳しく（最大500字）。
- 無駄を削ぎ落とし、要点だけを美しく簡潔に伝える。
- 可能な限り文学的・上質な表現で回答する。
- 過度に専門的になりすぎず、実用的なアドバイスを心がける。
- 必ず短く簡潔に伝えるようにしてください。
""",
            "material": """
# 背景・前提
あなたは資料研究をサポートするAIアシスタントです。  
ユーザーが提供した参考資料を分析し、執筆・研究・創作に役立つ情報を抽出することが役割です。

ユーザーからは以下の情報が提供されます：
- 参考資料：「=== 参考資料 ===」という見出しの下に、資料のタイトル、作成日時、本文が含まれています
- 会話履歴：「ユーザー:」「アシスタント:」という形式で過去のやり取りが記録されています

回答する際は、**提供された資料内容を必ず参照**し、  
**500字以内の簡潔かつ適切な回答**にすること。

# 判断するタスクの分類
ユーザーの依頼を読み、次のどれに該当するか分類してください。

a) 資料の重要ポイント抽出  
b) 背景知識・周辺知識の補足説明  
c) 創作への応用方法の提案  
d) 資料同士の関連性・比較分析  
e) 資料内容の解釈・要約依頼  
f) 資料非関連の質問（雑談・一般知識など）

# カテゴリ別対応方針

## a) 重要ポイント抽出
1. 提供された参考資料の内容を確認し、主要概念・要点を抽出する。  
2. 必要な情報を整理して提示（最大500字）。

## b) 背景知識の補足
1. 資料内で省略されている専門知識・歴史・概念を補足。  
2. 資料の理解を助ける範囲で簡潔に説明する（最大500字）。

## c) 創作への応用
1. 参考資料の内容をどのように物語・世界観・キャラクターへ応用できるか提案。  
2. 設定の幅を広げる具体例を提示する（最大500字）。

## d) 資料間の関連性分析
1. 提供された複数の参考資料を比較し、共通点・差異・因果関係を分析。  
2. 必要であれば構造化して提示する（最大500字）。

## e) 内容の解釈・要約
1. 参考資料の内容を要約し、論点・主張・流れを明確化。  
2. 誤読を避けるため、資料の原意を尊重して記述する（最大500字）。

## f) 資料非関連の場合
- 挨拶（「こんにちは」「おはよう」など）：簡潔に返す（例：「こんにちは！」）
- 簡単な雑談：1〜2文で対応
- 資料に無関係な質問：以下のように回答を拒否する  
「申し訳ありません。このアシスタントは資料研究専用です。  
　提供された資料に基づく質問であれば対応できます。」

# 重要な注意事項
- **質問の内容に応じて適切な長さで回答する**。挨拶には数文字、簡単な質問には短く、複雑な分析には詳しく（最大500字）。  
- 無駄に長くせず、必要な情報だけを簡潔に伝える。  
- 参考資料が提供されている場合は必ずその内容を参照して回答する。  
- 参考資料が提供されていない場合は、その旨を伝えて資料の提供を促す。  
- 背景補足は資料理解の助けになる範囲に留める。  
- 断定が難しい箇所は明確に「資料から読み取れる範囲では」と述べる。  
- 資料の誤用や不正確な推測は避ける。  
""",
        }

    async def generate_response(
        self, request: ChatRequest, chat_type: str = "general"
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

                            logger.info(
                                f"📖 [プロジェクト] Fetching {len(episode_ids)} episodes for book: {book_id}"
                            )
                            try:
                                episodes = await self.go_api_client.get_episodes_by_ids(
                                    book_id, episode_ids
                                )

                                if episodes:
                                    content_context += format_episodes_for_context(
                                        episodes
                                    )
                                    logger.info(
                                        f"✅ [プロジェクト] {len(episodes)} episodes loaded"
                                    )
                                else:
                                    logger.warning(
                                        f"⚠️ [プロジェクト] No episodes found for IDs: {episode_ids}"
                                    )
                                    content_not_found.append(f"project:{book_id}")
                            except Exception as e:
                                logger.error(
                                    f"❌ [プロジェクト] Error fetching episodes: {e}"
                                )
                                content_not_found.append(f"project:{book_id}")
                        elif len(parts) >= 2:
                            # book:book_id の形式（後方互換）
                            book_id = parts[1]
                            logger.warning(
                                f"⚠️ [プロジェクト] Legacy format 'book:{book_id}' - no episode IDs provided"
                            )
                            content_not_found.append(f"book:{book_id}")

            elif chat_type == "material" and request.sources:
                # 参考資料(materials)を取得
                logger.info(f"🔍 [資料] Processing sources: {request.sources}")
                for source in request.sources:
                    logger.info(f"🔍 [資料] Processing source: {source}")
                    # sourceの形式: "material:book_id:material_id1,material_id2,..." または "book:book_id"
                    if source.startswith("material:") or source.startswith("book:"):
                        parts = source.split(":")
                        logger.info(
                            f"🔍 [資料] Split parts: {parts}, length: {len(parts)}"
                        )
                        if len(parts) >= 3:
                            # material:book_id:material_ids の形式
                            book_id = parts[1]
                            material_ids = parts[2].split(",") if parts[2] else []

                            logger.info(
                                f"📚 [資料] Fetching {len(material_ids)} materials for book: {book_id}"
                            )
                            try:
                                materials = (
                                    await self.go_api_client.get_materials_by_ids(
                                        book_id, material_ids
                                    )
                                )

                                if materials:
                                    content_context += format_materials_for_context(
                                        materials
                                    )
                                    logger.info(
                                        f"✅ [資料] {len(materials)} materials loaded"
                                    )
                                else:
                                    logger.warning(
                                        f"⚠️ [資料] No materials found for IDs: {material_ids}"
                                    )
                                    content_not_found.append(f"material:{book_id}")
                            except Exception as e:
                                logger.error(f"❌ [資料] Error fetching materials: {e}")
                                content_not_found.append(f"material:{book_id}")
                        elif len(parts) >= 2:
                            # book:book_id の形式（後方互換）
                            book_id = parts[1]
                            logger.warning(
                                f"⚠️ [資料] Legacy format 'book:{book_id}' - no material IDs provided"
                            )
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
                    ts=int(time.time() * 1000),
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
                logger.info(f"Generated prompt length: {len(prompt)} characters")
            else:
                logger.info(f"Generated prompt: {prompt}")

            # Gemini APIを呼び出し
            logger.info(f"Generating response for chat_type: {chat_type}")

            # プロンプトが長すぎる場合は短縮
            if len(prompt) > 30000:  # 30KB制限
                logger.warning(f"Prompt too long ({len(prompt)} chars), truncating...")
                prompt = prompt[:30000] + "\n\n[プロンプトが長いため省略されました]"

            # GPT OSSのAPI設定
            gpt_oss_url = os.getenv(
                "GPT_OSS_URL"
            )
            gpt_oss_password = os.getenv("GPT_OSS_PASSWORD")

            # URLとパスワードが設定されているか確認
            if not gpt_oss_url:
                logger.error("GPT_OSS_URL environment variable is not set")
                import time

                return ChatMessage(
                    id=f"error-{int(time.time())}",
                    role="assistant",
                    content="GPT OSSのURLが設定されていません。管理者にお問い合わせください。",
                    ts=int(time.time() * 1000),
                )

            if not gpt_oss_password or gpt_oss_password == "Your-Pass-Word":
                logger.error(
                    "GPT_OSS_PASSWORD environment variable is not set or invalid"
                )
                import time

                return ChatMessage(
                    id=f"error-{int(time.time())}",
                    role="assistant",
                    content="GPT OSSのパスワードが設定されていません。管理者にお問い合わせください。",
                    ts=int(time.time() * 1000),
                )

            logger.info(
                f"Calling GPT OSS API... (password configured: {bool(gpt_oss_password)})"
            )

            headers = {
                "Content-Type": "application/json",
                "Authorization": gpt_oss_password,
            }

            payload = {"model": "gpt-oss:120b", "prompt": prompt, "stream": False}

            # GPT OSSのAPIを呼び出し
            response_obj = requests.post(
                gpt_oss_url, headers=headers, json=payload, verify=False, timeout=60
            )
            response_obj.raise_for_status()

            # レスポンスをパース
            response_data = response_obj.json()
            response_text = (
                html.unescape(response_data.get("response", ""))
                .replace("<br>", "\n")
                .replace("<br/>", "\n")
                .replace("<br />", "\n")
            )

            # レスポンスの検証（GPT OSSのレスポンス形式に対応）
            if not response_text or not response_text.strip():
                logger.warning("Empty response text received from GPT OSS")
                response_text = "申し訳ございません。AIからの応答が空でした。"

            # 空のレスポンスの場合のフォールバック
            if not response_text.strip():
                logger.warning("Empty response text received")
                data_type_ja = (
                    "プロジェクト"
                    if chat_type == "project"
                    else "参考資料" if chat_type == "material" else "データ"
                )
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
                ts=int(time.time() * 1000),
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
                content = (
                    f"申し訳ございません。エラーが発生しました: {error_message[:100]}"
                )

            # エラー時のフォールバック
            import time

            return ChatMessage(
                id=f"error-{int(time.time())}",
                role="assistant",
                content=content,
                ts=int(time.time() * 1000),
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
                        if hasattr(part, "text") and part.text:
                            text_parts.append(part.text)
                    response_text = "".join(text_parts)
                else:
                    response_text = f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"
            else:
                response_text = (
                    f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"
                )

            return (
                response_text
                if response_text.strip()
                else f"「{query}」について調査中です。詳細な情報は後ほど提供いたします。"
            )

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
