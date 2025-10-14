import argparse
import os
from pathlib import Path
from typing import List

import yaml
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMupdfLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


def load_settings(settings_path: Path) -> dict:
    if settings_path.exists():
        with settings_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def collect_documents(input_path: Path) -> List:
    """
    Collect Markdown,txt or pdf documents from a file or directory.
    - If file: supports .md/.markdown/.txt or .pdf
    - If directory: scans for .md/.markdown/.txt or .pdf recursively
    """
    docs = []
    targets: List[Path] = []
    if input_path.is_file():
        targets = [input_path]
    else:
        targets = (
            sorted(input_path.glob("**/*.md"))
            + sorted(input_path.glob("**/*.markdown"))
            + sorted(input_path.glob("**/*.txt"))
            + sorted(input_path.glob("**/*.pdf"))
        )

    for p in targets:
        try:
            if p.suffix.lower() in {".md", ".markdown", ".txt"}:
                loader = TextLoader(str(p), encoding="utf-8")
                docs.extend(loader.load())
            elif p.suffix.lower() in {".pdf"}:
                loader = PyMupdfLoader(str(p))
                docs.extend(loader.load())
            else:
                print(f"Warning: unsupported file type {p}, skipping")

        except Exception as e:
            print(f"Warning: failed to load {p}: {e}")
    return docs


def main():
    parser = argparse.ArgumentParser(description="Build FAISS index from Markdown/TXT sources under llm/")
    parser.add_argument("--input", default="llm", help="Path to a file or directory containing .md/.txt/.pdf")
    parser.add_argument("--out", default="artifacts", help="Output directory for FAISS index")
    parser.add_argument("--chunk_size", type=int, default=800, help="Chunk size in characters")
    parser.add_argument("--chunk_overlap", type=int, default=200, help="Chunk overlap in characters")
    parser.add_argument("--model", default="text-embedding-3-small", help="OpenAI embeddings model")
    parser.add_argument("--peek", type=int, default=0, help="Print first N chunks for inspection")
    args = parser.parse_args()

    # Load environment from .env and .env.local (latter overrides)
    load_dotenv(dotenv_path=Path(".env"))
    load_dotenv(dotenv_path=Path(".env.local"), override=True)

    input_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    _ = load_settings(Path("config/settings.yml"))

    # Collect
    documents = collect_documents(input_path)
    if not documents:
        print(f"No source files found under {input_path}. Place .md/.txt and rerun.")
        return

    # Split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        separators=["\n\n", "\n", "。", "、", " "]
    )
    splits = splitter.split_documents(documents)
    print(f"Loaded {len(documents)} pages -> {len(splits)} chunks")
    if not splits:
        total_chars = sum(len((d.page_content or "")) for d in documents)
        print(
            "No text chunks produced. Details:"
            f" documents={len(documents)}, total_chars={total_chars},"
            f" chunk_size={args.chunk_size}, chunk_overlap={args.chunk_overlap}"
        )
        print(
            "Check that your Markdown files exist and have content.\n"
            "If running via Docker, ensure the llm/ folder is mounted."
        )
        return
    if args.peek > 0:
        print("--- Peek chunks ---")
        for i, d in enumerate(splits[: args.peek]):
            txt = (d.page_content or "").replace("\n", " ")
            print(f"[{i+1}] {txt[:200]}")

    # Embeddings + FAISS
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Put it in .env.local or .env")
    embeddings = OpenAIEmbeddings(model=args.model)
    vectordb = FAISS.from_documents(splits, embeddings)

    # Save
    vectordb.save_local(str(out_dir))
    print(f"Saved FAISS index to {out_dir}")


if __name__ == "__main__":
    main()
