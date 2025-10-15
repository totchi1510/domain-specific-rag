# ワークショップ用 README（PDFローダー×RAG 比較）

このドキュメントは勉強会（ワークショップ）向けです。PDF解析ツール（ローダー）の違いが「インデックス作成の速さ」と「RAG の挙動（精度・fallback）」に与える影響を体感します。

## ゴール
- 同じ教材に対して複数ローダーでインデックスを作成し、処理時間・チャンク数を比較する
- 同じ質問を API に投げ、fallback の有無や回答内容の違いを観察する

## 前提
- Docker / Docker Compose が使えること
- OpenAI API キー（埋め込み生成に使用）

## セットアップ（最短）
1) 依存のビルド
- `docker compose build`

2) API キー設定
- `.env.example` をコピーして `.env.local` を作成し、`OPENAI_API_KEY=sk-...` を記入

3) 教材を配置
- `llm/` 配下に `.pdf` / `.md` / `.txt` を置く（既存の教材がある場合はそのまま）

## インデックス作成（ローダー別）
以下のようにローダーを切り替えて実行します。所要時間とコンソールの統計を記録してください。

- 例: PDFium2（推奨）
  - `docker compose run --rm indexer --reading_tool pdfium2 --input /app/llm --out /app/artifacts --peek 3`
- 他の例（順次比較）
  - `--reading_tool pymupdf`
  - `--reading_tool pypdf`
  - `--reading_tool pdfplumber`
  - `--reading_tool pdfminer`

観察ポイント（ログに表示されます）
- `Loaded X pages -> Y chunks`（ページ数とチャンク数）
- `load_file_time_sec=...`（読み込み〜分割までの時間の目安）

同じ `llm/` 入力でローダーを変え、上記2点を記録・比較してください。

## API 起動と疎通
- 起動: `docker compose up -d api`
- ヘルス: `curl http://127.0.0.1:8000/healthz` → `{ "ok": true }` で準備OK

## ACCEPTANCE テスト（手動で実行）
`docs/acceptance_test.yml` に、質問 (`question`) と期待 (`expected`) が定義されています。以下の手順で手動実行・確認します。

1) 対象テストを開く
- `docs/acceptance_test.yml` をエディタで開き、`name` と `question` を確認
  - 例: `out_of_scope_credentials`（期待: `fallback: true`）
  - 例: `ims_compare_methods`（期待: 回答に特定語が含まれる）

2) API に質問を送る（例: curl）
- `curl -s -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d "{\"question\":\"<ここに question を貼る>\"}"`

3) 応答を確認
- 応答 JSON 例: `{ "answer": "...", "fallback": false }`
- 期待の読み方（YAML の `expected` を参照）
  - `type: fallback` の場合 → `fallback: true` であること
  - `must_include: ["...", ...]` → `answer` にこれらの語が含まれること
  - `must_not_include: ["...", ...]` → `answer` に含まれないこと

4) ローダー切替で再確認
- 別ローダーで再度インデックスを作成（上書き）し、`docker compose restart api`
- 同じ質問を投げ、`fallback` の有無や回答の差を比較

ヒント:
- out-of-scope 系（資格情報・ベンダー個別情報など）は多くの教材で `fallback: true` が期待されます
- 定義や用語説明（例: “Boundary Spanning” を含む質問）は、関連語が回答に含まれるかを確認します

## よくある質問 / トラブルシュート
- `healthz` が `ok:false` のまま
  - インデックスが存在しない、または OpenAI キー未設定です
  - 対処: インデックス作成をやり直し、`.env.local` のキーを確認
- Windows でファイル共有に失敗
  - Docker Desktop の共有設定で、このリポジトリのフォルダを許可してください
- 速度だけ見たい（キーを共有できない場合）
  - 講師側で実行して画面共有するか、事前に作成した `artifacts/` を配布して API の挙動だけを体験してください

## 補足
- 既存のプロダクト向け README は `README.product.md` に移動しました（API の詳細利用はこちらを参照）

