# Domain RAG MVP (JA→EN retrieval, JA answer)

このリポジトリは、Markdown/TXTのナレッジをFAISSに索引し、質問を受けてRAGで回答する最小構成のMVPです。質問文は日本語、コーパスは英語でも運用できるよう、Config B（JP→EN 翻訳→EN検索→JA回答）を実装しています。

## 主要機能
- ナレッジ取り込み: `llm/*.md` / `*.txt` を再帰的に読み込み → 分割 → OpenAI Embeddings → FAISS 保存
- API: FastAPI `POST /ask`（`{question}` → `{answer, fallback}`）
  - 閾値未満は `fallback: true` で問い合わせ導線を提示
  - 設定で JP→EN 翻訳を有効化し、英語コーパスに対して検索
- UI: シンプルなチャット画面（`/` で配信）
- 受入テスト: YAML定義を一括実行するランナー（正答・フォールバック判定）

## クイックスタート（Docker）
1. 事前準備
   - `llm/data.md`（または複数の `.md/.txt`）を配置
   - `.env.local` に `OPENAI_API_KEY` を設定
2. ビルド
   - `docker compose build`
3. 索引作成（初回/更新時）
   - `docker compose run --rm indexer`
     - 先頭チャンクを確認したい場合: `docker compose run --rm indexer python scripts/build_index.py --input /app/llm --out /app/artifacts --peek 8`
4. API起動
   - `docker compose up -d api`
   - ヘルス: `curl http://127.0.0.1:8000/healthz` / `.../healthz_detail`
5. UI
   - ブラウザで `http://127.0.0.1:8000/`
6. 受入テスト
   - `docker compose exec api python scripts/run_acceptance_tests.py --file /app/docs/acceptance_test.yml --base-url http://127.0.0.1:8000`

## 設定ファイル `config/settings.yml`
例:

```
threshold: 0.50
top_k: 5
google_form_url: "https://example.com/form"

# Config B: JP→EN 検索、JAで回答
translate_query: true
doc_lang: "en"
answer_lang: "ja"
```

ヒント:
- 回答が `fallback` に寄りすぎる場合は `threshold` を下げる（例: 0.30〜0.50）。
- 見つけにくい場合は `top_k` を増やす（3→5）。

## よくあるトラブル
- Compose の警告: `version is obsolete`
  - `docker-compose.yml` の `version:` 行を削除してください（本リポは対応済みの場合あり）。
- `/healthz` が `ok:false`
  - `OPENAI_API_KEY` 未設定、またはFAISS未作成。上の手順3を実行。
- 常に `fallback:true`
  - ナレッジ内に期待語彙がない/分割が粗い/閾値が高い可能性。`--peek` でチャンク確認 → データや `threshold` 調整。

## ディレクトリ構成
- `llm/` ナレッジ（Markdown/TXT）
- `artifacts/` FAISSインデックス（生成物）
- `api/` FastAPIアプリ
- `web/` 最小UI（静的配信）
- `scripts/` インデクサ・テストなど
- `docs/` 仕様・開発手順・受入テスト定義

## API 一覧
- `POST /ask` → `{answer, fallback}`
- `GET /healthz` / `GET /healthz_detail`
- `GET /config_public`（UI用の公開設定）

## 開発メモ
- 学習済み埋め込みは `text-embedding-3-small`（多言語対応）
- 検索スコアは距離を `1/(1+d)` で正規化。スケールに合わせ `threshold` は低めから試す。
- 受入テストは `docs/acceptance_test.yml` を編集して領域に合わせる。

