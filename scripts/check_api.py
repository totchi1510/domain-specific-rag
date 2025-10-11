from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add repo root to sys.path so we can import api.main
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app


def main():
    with TestClient(app) as client:
        r = client.get("/healthz")
        print("/healthz:", r.status_code, r.json())

        rd = client.get("/healthz_detail")
        print("/healthz_detail:", rd.status_code, rd.json())

        # 通常の質問で疎通確認（埋め込みAPIを1回呼びます）
        r2 = client.post("/ask", json={"question": "申請の締切はいつですか？"})
        print("/ask:", r2.status_code, r2.json())


if __name__ == "__main__":
    main()
