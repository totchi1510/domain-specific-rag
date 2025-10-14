# Domain RAG MVP — User Guide

このREADMEは「同じようにこのサイトを使える」ための手順に特化しています。設計・仕様の詳細は `docs/specification.md` を参照してください。

目的
- 日本語のpdfをナレッジにし、日本語の質問に自動回答します（JP→JA回答）。

前提
- Docker/Docker Compose が利用できる
- OpenAI APIキーがある（`.env.local` に設定）

セットアップ（最短5分）
1) ナレッジを置く
- `llm/` 配下に `.pdf`もしくは`.txt`、`.md`を置く

2) APIキーを設定
- `.env.local` を作成し、以下を記載
```
OPENAI_API_KEY=sk-...
```

3) 設定を確認（任意）
- `config/settings.yml`（既定値のままでも動作）
```
threshold: 0.50
top_k: 5
google_form_url: "https://example.com/form"
translate_query: true
doc_lang: "en"
answer_lang: "ja"
```

4) コンテナをビルド
- `docker compose build`

5) 索引を作成（初回/更新時）
- `docker compose run --rm indexer`
- チャンク確認（任意）: `docker compose run --rm indexer python scripts/build_index.py --input /app/llm --out /app/artifacts --peek 8`

6) APIを起動
- `docker compose up -d api`
- ヘルス: `curl http://127.0.0.1:8000/healthz`（`{"ok": true}` ならOK）

7) Webサイトを使う
- ブラウザで `http://127.0.0.1:8000/`
- 質問を入力して送信。該当が弱い場合は「お問い合わせ」ボタンが表示されます。

更新フロー（ナレッジを修正/追加したら）
1) `llm/` の `.md/.txt` を更新
2) 索引作成を再実行: `docker compose run --rm indexer`
3) API再起動: `docker compose restart api`

トラブルシュート
- 常に `fallback: true`
  - ナレッジ内に期待語彙が無い／分割が粗い／閾値が高い可能性
  - 対策: `--peek` でチャンクを確認、`threshold` を 0.30〜0.50 で調整、`top_k` を 3→5へ
- `/healthz` が `ok:false`
  - APIキー未設定、または索引未作成
  - 対策: `.env.local` を確認、手順5を実行
- Composeの警告（version obsolete）
  - 本リポは `version:` を削除済み。警告が出る場合はComposeのバージョンを確認

参考（任意）
- 受入テストをまとめて実行: 
  - `docker compose exec api python scripts/run_acceptance_tests.py --file /app/docs/acceptance_test.yml --base-url http://127.0.0.1:8000`
- 仕様・開発手順: `docs/specification.md`, `docs/dev_steps.md`
