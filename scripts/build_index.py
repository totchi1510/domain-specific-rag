import argparse
import os
import time
from pathlib import Path
from typing import List

import yaml
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader, PyPDFLoader, PyPDFium2Loader, PDFPlumberLoader, PDFMinerLoader
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
# from langchain_unstructured import UnstructuredLoader　 errorになるのでコメントアウト
#from langchain_docling import DoclingLoader   docling はやってもいいが、インストールが重いので保留
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

def load_settings(settings_path: Path) -> dict:
    if settings_path.exists():
        with settings_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def pdfloader(r_tool: str, input_path: Path):
    """PDF ローダーを返す。選択肢は以下の通り。
    - pymupdf: PyMuPDF (fitz) ベースのローダー
    - pymupdf4llm: PyMuPDF4LLM ベースのローダー
    - pypdf: PyPDF2 ベースのローダー
    - pdfplumber: pdfplumber ベースのローダー
    - auto: pymupdf -> pypdf -> pdfplumber の順で試
    失敗した場合は例外を投げる。
    """
    try:
        if r_tool == "pymupdf":
            return PyMuPDFLoader(str(input_path))
        elif r_tool == "pymupdf4llm":
            return PyMuPDF4LLMLoader(str(input_path))
        elif r_tool == "pypdf":
            return PyPDFLoader(str(input_path))
        elif r_tool == "pdfium2":
            return PyPDFium2Loader(str(input_path))
        elif r_tool == "pdfplumber":
            return PDFPlumberLoader(str(input_path))
        elif r_tool == "pdfminer":
            return PDFMinerLoader(str(input_path))
        #elif r_tool == "unstructured":
            #return UnstructuredLoader(str(input_path))
        #elif r_tool == "docling":
            #return DoclingLoader(str(input_path))

    except Exception as e:
        raise ValueError(f"Unknown reading_tool: {r_tool}")



def collect_documents(r_tool: str, input_path: Path) -> List:
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
                loader = pdfloader(r_tool, p)
                docs.extend(loader.load())
            else:
                print(f"Warning: unsupported file type {p}, skipping")

        except Exception as e:
            print(f"Warning: failed to load {p}: {e}")
    return docs


def main():

    parser = argparse.ArgumentParser(description="Build FAISS index from Markdown, txt or pdf sources under llm/")
    parser.add_argument("--input", default="llm", help="Path to a file or directory containing .md/.txt/.pdf")
    parser.add_argument("--out", default="artifacts", help="Output directory for FAISS index")
    parser.add_argument("--chunk_size", type=int, default=800, help="Chunk size in characters")
    parser.add_argument("--chunk_overlap", type=int, default=200, help="Chunk overlap in characters")
    parser.add_argument("--model", default="text-embedding-3-small", help="OpenAI embeddings model")
    parser.add_argument("--peek", type=int, default=0, help="Print first N chunks for inspection")
    parser.add_argument(
        "--reading_tool",
        default="pymupdf",
        choices=[
            "pymupdf",
            "pymupdf4llm",
            "pypdf",
            "pdfplumber",
            "pdfium2",
            "pdfminer",
        ],
        help="PDF reader to use (pymupdf/pymupdf4llm/pypdf/pdfplumber/pdfium2/pdfminer)",
    )
    args = parser.parse_args()

    # Load environment from .env and .env.local (latter overrides)
    load_dotenv(dotenv_path=Path(".env"))
    load_dotenv(dotenv_path=Path(".env.local"), override=True)

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: input path {input_path} does not exist")
        return

    out_dir = Path(args.out)

    out_dir.mkdir(parents=True, exist_ok=True)

    _ = load_settings(Path("config/settings.yml"))

    r_tool = args.reading_tool

    t0 = time.perf_counter()

    # Collect
    documents = collect_documents(r_tool, input_path)

    dt = time.perf_counter()-t0

    if not documents:
        print(f"No source files found under {input_path}. Place .md/.txt/.pdf and rerun.")
        return

    # split
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
    print(f"load_file_time_sec={dt:.2f} ")


if __name__ == "__main__":
    main()
