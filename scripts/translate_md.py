import argparse
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def chunks_by_lines(text: str, max_chars: int = 6000) -> List[str]:
    buf: List[str] = []
    cur = []
    size = 0
    for line in text.splitlines(True):
        if size + len(line) > max_chars and cur:
            buf.append("".join(cur))
            cur = []
            size = 0
        cur.append(line)
        size += len(line)
    if cur:
        buf.append("".join(cur))
    return buf


def translate_md(inp: Path, outp: Path, model: str = "gpt-4o-mini"):
    load_dotenv(Path(".env"))
    load_dotenv(Path(".env.local"), override=True)
    src = inp.read_text(encoding="utf-8")
    parts = chunks_by_lines(src)
    chat = ChatOpenAI(model=model, temperature=0.0)
    out_lines: List[str] = []
    for i, part in enumerate(parts, 1):
        res = chat.invoke([
            ("system", "Translate the following Markdown from Japanese to English.\n"
                        "- Keep Markdown structure, headings, lists, code fences.\n"
                        "- Do not add explanations; output English Markdown only."),
            ("user", part),
        ])
        out_lines.append(res.content.strip())
    outp.write_text("\n\n".join(out_lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Translate Markdown JA->EN using OpenAI Chat")
    ap.add_argument("input", help="Input Markdown path (e.g., llm/data.md)")
    ap.add_argument("output", help="Output Markdown path (e.g., llm/data.en.md)")
    ap.add_argument("--model", default="gpt-4o-mini", help="Chat model")
    args = ap.parse_args()
    translate_md(Path(args.input), Path(args.output), model=args.model)


if __name__ == "__main__":
    main()

