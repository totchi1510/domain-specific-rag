# 開発STEP（MVP）

## フェーズ0 準備・仕様固め
- 問い合わせフォームURL確定（`config/settings.yml`）
- 受入テスト10問のドラフト（`docs/acceptance_test.yml`）
- 閾値/Top-k 暫定: `threshold=0.50`、`top_k=5`（後で調整）

## フェーズ1 オフライン索引（Markdown）
- 入力: `llm/*.md`/`*.txt`
- 分割: 800/200（`scripts/build_index.py`）
- 埋め込み: OpenAI Embeddings → FAISS 保存（`artifacts/`）
- 実行: `docker compose run --rm indexer`

## フェーズ2 API 最小実装
- FastAPI `POST /ask`（`{question}` → `{answer, fallback}`）
- 起動時にFAISS読み込み、Retriever化
- Config B: JP→EN 翻訳→EN検索→JA回答
- 簡易レート制限、ヘルスエンドポイント

## フェーズ3 UI 最小チャット
- 単一ページ（入力/送信/回答/ローディング）
- fallback: true でフォームボタン強調
- `GET /config_public` でリンク等を取得

## フェーズ4 MVP検証・微調整
- 受入テスト10問を実行（`scripts/run_acceptance_tests.py`）
- 閾値/Top-k 調整、チャンク戦略の見直し
- コスト/応答時間の計測と短縮（回答長/Top-k調整）

## フェーズ5 運用設計
- リリースタグ（例）: `kb-YYYYMMDD`（索引版）+ `app-v0.x`
- 更新手順: Markdown→再インデックス→API再起動
- 監視: リクエスト数／fallback率／エラー

## 拡張（任意）
- 👍👎 フィードバック収集
- FAQ静的ページの自動生成
- 出典スニペットの任意ON
- 検索・検証ループ（LangGraph）／評価（Ragas）

