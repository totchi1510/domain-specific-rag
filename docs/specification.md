# 仕様書（MVP）— ドメイン特化型 LLM Web サイト

## 1. 概要
英語のMarkdown/TXTナレッジに基づき、Web 来訪者の日本語質問へ自動回答するRAGのMVP。Config B（JP→EN 翻訳→EN検索→JA回答）を採用し、英語コーパスでも日本語UXを維持します。

## 2. 対象・利用シナリオ
- 対象: 自サイトのFAQ/ガイドの自動応答（一般公開）
- 典型質問: 概要、定義、年次、用語解説、規模、枠組み等
- 不明時導線: 問い合わせフォーム（MVPは出典非表示）

## 3. 機能要件
3.1 コア機能
- F1 質問受付: 日本語テキストを受理
- F2 回答生成: 英語コーパスを参照して日本語で簡潔回答
- F3 不明時誘導: 閾値未満は問い合わせリンク提示（fallback: true）
- F4 API提供: `POST /ask` → `{answer, fallback}`
- F5 ナレッジ更新: Markdown更新→再インデックス→再起動

3.2 UI（MVP）
- 単一ページのチャットUI（入力・送信・回答表示・ローディング）
- fallback: true の場合は問い合わせボタンを強調

## 4. 非機能要件
- 実装: Python（FastAPI, LangChain）
- ホスティング: Docker（API/静的配信）
- コスト: OpenAIは最小トークン
- 性能: p50 ≤ 3s, p95 ≤ 8s を目安
- セキュリティ: 公開情報のみ取り扱い（個人情報の保存なし）
- 多言語: MVPは日本語UI固定／英語コーパス

## 5. アーキテクチャ
`[Web UI] -- POST /ask --> [API(FastAPI)] -- Retriever(FAISS) -- LLM(OpenAI)`

`[Markdown/TXT] --(オフライン: 分割/埋め込み/索引生成)--> [FAISS artifacts]`

## 6. LLM・RAGポリシー
- LLM: OpenAI（日本語で簡潔回答。英語固有名詞は括弧で併記）
- Embeddings: OpenAI（多言語）
- チャンク: 800/200（調整可）
- Top-k: 3〜5、閾値: 0.30〜0.50 から評価
- Config B:
  - `translate_query: true`
  - `doc_lang: en`
  - `answer_lang: ja`

## 7. API I/F
- `POST /ask`
  - Req: `{ "question": "iMSとは？" }`
  - Res(成功): `{ "answer": "...", "fallback": false }`
  - Res(不明): `{ "answer": "該当情報が見つかりません...<URL>", "fallback": true }`
- `GET /healthz` / `GET /healthz_detail`

## 8. 運用
- ナレッジ: `llm/*.md` 配置
- 再インデックス: `docker compose run --rm indexer`
- 再起動: `docker compose restart api`
- 監視: リクエスト数／fallback率

## 9. 受け入れ基準
- 10問中8問以上が適切回答
- 残りは確実にフォーム誘導
- 応答性能は目標範囲内

## 10. リスク
- 無料枠・レート制限 → 回答長・レート制御
- 抽出品質 → Markdownの語彙・構造を明確化
- コールドスタート → 必要に応じ常時稼働等

