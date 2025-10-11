import os
import time
from pathlib import Path
from typing import List, Tuple

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    fallback: bool


def load_settings() -> dict:
    cfg = Path("config/settings.yml")
    if cfg.exists():
        with cfg.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_env():
    load_dotenv(dotenv_path=Path(".env"))
    load_dotenv(dotenv_path=Path(".env.local"), override=True)


app = FastAPI(title="Domain RAG API", version="0.2.0")

_settings = {}
_embeddings = None
_vectordb: FAISS | None = None
_chat: ChatOpenAI | None = None

# very simple in-memory rate limiter
_rate_bucket = {}
_RATE_LIMIT = {"capacity": 10, "window_sec": 10}


@app.on_event("startup")
def _startup():
    global _settings, _embeddings, _vectordb, _chat
    load_env()
    _settings = load_settings()

    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    _chat = ChatOpenAI(model=model, temperature=0.2)

    _embeddings = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))

    artifacts_dir = Path("artifacts")
    if not (artifacts_dir / "index.faiss").exists():
        raise RuntimeError("FAISS index not found. Build it via scripts/build_index.py")
    _vectordb = FAISS.load_local(str(artifacts_dir), _embeddings, allow_dangerous_deserialization=True)


def _rate_limit_ok(key: str) -> bool:
    cap = _RATE_LIMIT["capacity"]
    win = _RATE_LIMIT["window_sec"]
    now = time.time()
    hist: List[float] = _rate_bucket.get(key, [])
    hist = [t for t in hist if now - t < win]
    if len(hist) >= cap:
        _rate_bucket[key] = hist
        return False
    hist.append(now)
    _rate_bucket[key] = hist
    return True


def _search_with_scores(query: str, k: int) -> List[Tuple[str, float]]:
    assert _vectordb is not None
    # Prefer relevance scores in [0,1] if available; fallback to distance -> pseudo-relevance
    if hasattr(_vectordb, "similarity_search_with_relevance_scores"):
        hits = _vectordb.similarity_search_with_relevance_scores(query, k=k)
        return [(doc.page_content, float(score)) for doc, score in hits]
    else:
        hits = _vectordb.similarity_search_with_score(query, k=k)
        # score is a distance; normalize to (0,1]
        return [(doc.page_content, 1.0 / (1.0 + float(score))) for doc, score in hits]


@app.post("/ask", response_model=AskResponse)
def ask(req: Request, payload: AskRequest) -> AskResponse:
    client_ip = req.client.host if req.client else "unknown"
    if not _rate_limit_ok(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    q = (payload.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="question is required")

    threshold = float(_settings.get("threshold"))
    top_k = int(_settings.get("top_k"))
    form_url = _settings.get("google_form_url")

    hits = _search_with_scores(q, k=top_k)
    if not hits:
        msg = f"該当情報が見つかりません。こちらからお問い合わせください: {form_url}"
        return AskResponse(answer=msg, fallback=True)

    best_sim = hits[0][1]
    if best_sim < threshold:
        msg = f"該当情報が見つかりません。こちらからお問い合わせください: {form_url}"
        return AskResponse(answer=msg, fallback=True)

    context = "\n\n".join([c for c, _ in hits])[:4000]

    sys_msg = (
        "あなたは日本語で簡潔に答えるアシスタントです。"
        "与えられたコンテキストに基づいて、事実のみを短く回答してください。"
        "不明確な場合は推測せず、フォーム誘導が適切な場合は誘導してください。"
    )
    user_msg = (
        f"質問:\n{q}\n\n"
        f"コンテキスト:\n{context}\n"
    )

    assert _chat is not None
    result = _chat.invoke([
        ("system", sys_msg),
        ("user", user_msg),
    ])
    answer = result.content.strip() if hasattr(result, "content") else str(result)
    return AskResponse(answer=answer, fallback=False)


# Health check
@app.get("/healthz")
def healthz():
    ok = _vectordb is not None and _chat is not None
    return {"ok": ok}
