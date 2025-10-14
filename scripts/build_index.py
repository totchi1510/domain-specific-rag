import argparse
import os
import time
from pathlib import Path
from typing import List

import yaml
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader, PyPDFLoader, PyPDFium2Loader, PDFPlumberLoader
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

def load_settings(settings_path: Path) -> dict:
    if settings_path.exists():
        with settings_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def pdfloader(r_tool: str, input_path: Path):
    """PDF 繝ｭ繝ｼ繝繝ｼ繧定ｿ斐☆縲る∈謚櫁い縺ｯ莉･荳九・騾壹ｊ縲・    - pymupdf: PyMuPDF (fitz) 繝吶・繧ｹ縺ｮ繝ｭ繝ｼ繝繝ｼ
    - pymupdf4llm: PyMuPDF4LLM 繝吶・繧ｹ縺ｮ繝ｭ繝ｼ繝繝ｼ
    - pypdf: PyPDF2 繝吶・繧ｹ縺ｮ繝ｭ繝ｼ繝繝ｼ
    - pdfplumber: pdfplumber 繝吶・繧ｹ縺ｮ繝ｭ繝ｼ繝繝ｼ
    - auto: pymupdf -> pypdf -> pdfplumber 縺ｮ鬆・〒隧ｦ
    螟ｱ謨励＠縺溷ｴ蜷医・萓句､悶ｒ謚輔￡繧九・    """
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
            "docling",
            "auto",
        ],
        help="PDF reader to use (pymupdf/pymupdf4llm/pypdf/pdfplumber/pdfium/docling/auto)",
    )
    args = parser.parse_args()

    # Load environment from .env and .env.local (latter overrides)
    load_dotenv(dotenv_path=Path(".env"))
    load_dotenv(dotenv_path=Path(".env.local"), override=True)

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: input path {input_path} does not exist")
        return
    _ = load_settings(Path("config/settings.yml"))

    r_tool = args.reading_tool

    # Measure only the load time and exit
    t_load0 = time.perf_counter()
    documents = collect_documents(r_tool, input_path)
    load_sec = time.perf_counter() - t_load0
    print(f'loaded_docs={len(documents)}')
    print(f'load_time_sec={load_sec:.2f}')
    return
    # Indexing pipeline intentionally skipped in load-only mode
