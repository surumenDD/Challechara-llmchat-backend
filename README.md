# Challechara Backend

作家支援アプリケーション「Challechara」のバックエンドAPI

## 概要

このバックエンドは、Gemini APIを使用したチャット機能を提供する FastAPI
アプリケーションです。

## 機能

- **プロジェクトチャット**: プロジェクトファイルを参照したAIチャット
- **辞書・表現検索**: 単語・表現の検索とチャット
- **資料チャット**: GoバックエンドのエピソードデータをGoAPIから取得してLLMに質問
- **資料管理**: GoバックエンドAPI経由でエピソードを管理

## セットアップ

### クイックスタート（再現手順）

```bash
# 1. バックエンドディレクトリに移動
cd backend/

# 2. 仮想環境の作成・有効化（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 3. 依存関係のインストール
pip install -r requirements.txt --only-binary=pydantic

# 4. 環境変数の設定
cp .env.example .env
# .envファイルを編集してGEMINI_API_KEYを設定

# 5. サーバー起動
python main.py
# ブラウザで http://localhost:8000/docs にアクセスしてAPIドキュメントを確認
```

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` を `.env` にコピーして、必要な値を設定してください：

```bash
cp .env.example .env
```

`.env` ファイルを編集：

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
DEBUG=True
PORT=8000
FRONTEND_URL=http://localhost:3000
GO_API_URL=http://localhost:8080  # GoバックエンドのURL
```

### 3. Gemini API キーの取得

1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
2. APIキーを生成
3. `.env` ファイルの `GEMINI_API_KEY` に設定

### 4. サーバーの起動

#### Docker Composeで起動（推奨）

```bash
# Dockerコンテナをビルド＆起動
docker compose up -d

# ログを確認
docker compose logs -f app

# 停止
docker compose down
```

#### ローカル環境で起動

```bash
python main.py
```

または

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API エンドポイント

### チャット機能

- `POST /api/chat/project` - プロジェクトファイル参照チャット
- `POST /api/chat/dictionary` - 辞書・表現検索チャット
- `POST /api/chat/material` - GoAPIからエピソードを取得してLLMに質問

**資料チャットの使い方:**

```json
{
  "messages": [
    {
      "id": "1",
      "role": "user",
      "content": "このエピソードについて教えて",
      "ts": 1638360000000
    }
  ],
  "sources": ["book:123"] // book_idを指定
}
```

### 辞書機能

- `GET /api/dictionary/search?query={word}` - 辞書検索
- `GET /api/dictionary/suggest?context={context}` - 表現提案

## アーキテクチャ

```
Pythonバックエンド (このリポジトリ)
  ├── Gemini API (LLM)
  └── Go Backend API (データ取得)
       └── MySQL (エピソードデータ)
```

GoバックエンドAPIから`/books/{id}/episodes`エンドポイントを使ってエピソードデータを取得し、LLMに渡します。

- `POST /api/materials/{book_id}/bulk-upload` - 一括アップロード

### ヘルスチェック

- `GET /` - API情報
- `GET /health` - ヘルスチェック

## フロントエンドとの連携

### chatProvider.tsの修正

フロントエンドの `lib/chatProvider.ts` を以下のように変更してください：

```typescript
// 既存のMockProviderをAPIProviderに置き換え
export class APIProvider implements ChatProvider {
  private baseURL: string;

  constructor(baseURL: string = "http://localhost:8000/api") {
    this.baseURL = baseURL;
  }

  async send(
    messages: ChatMessage[],
    opts: { sources?: string[]; chatType?: string } = {},
  ): Promise<ChatMessage> {
    const { sources = [], chatType = "project" } = opts;

    const endpoint = {
      "project": "/chat/project",
      "dictionary": "/chat/dictionary",
      "material": "/chat/material",
    }[chatType] || "/chat/project";

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages,
        sources,
      }),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    const data = await response.json();
    return data.message;
  }
}

// プロバイダーファクトリーを更新
export function createChatProvider(): ChatProvider {
  if (process.env.NODE_ENV === "development") {
    return new APIProvider(); // 本番環境でも使用
  } else {
    return new APIProvider("https://your-backend-api.com/api");
  }
}
```

## プロジェクト構造

```
backend/
├── main.py                 # FastAPI アプリケーション
├── requirements.txt        # 依存関係
├── .env.example           # 環境変数テンプレート
├── models/
│   ├── __init__.py
│   └── schemas.py         # Pydantic モデル
├── routers/
│   ├── __init__.py
│   ├── chat.py            # チャットAPI
│   ├── dictionary.py      # 辞書API
│   └── materials.py       # 資料管理API
├── services/
│   ├── __init__.py
│   └── gemini_service.py  # Gemini API サービス
└── data/
    └── materials/         # アップロードファイル保存場所
```

## 開発メモ

- **認証**: 現在は実装していません。必要に応じて JWT 認証などを追加してください
- **データベース**: 現在はインメモリストレージを使用。本番環境では PostgreSQL や
  MongoDB などの使用を推奨
- **ファイルストレージ**: ローカルファイルシステムを使用。本番環境では AWS S3
  などのクラウドストレージを推奨
- **ログ**: 基本的なログを実装。本番環境では構造化ログの使用を推奨

## トラブルシューティング

### Gemini API エラー

1. API キーが正しく設定されているか確認
2. API クォータが残っているか確認
3. ネットワーク接続を確認

### CORS エラー

`main.py` の CORS 設定でフロントエンドのURLが許可されているか確認してください。

### ポートエラー

他のアプリケーションがポート 8000 を使用している場合、`.env`
ファイルで別のポートを指定してください。
