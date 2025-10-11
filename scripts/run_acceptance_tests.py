import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
import yaml


@dataclass
class Expected:
    type: str  # "answer" | "fallback"
    must_include: List[str]
    must_not_include: List[str]


@dataclass
class Case:
    name: str
    question: str
    expected: Expected


def load_cases(path: Path) -> List[Case]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases: List[Case] = []
    for it in data.get("cases", []):
        exp = it.get("expected", {})
        cases.append(
            Case(
                name=str(it.get("name")),
                question=str(it.get("question", "")).strip(),
                expected=Expected(
                    type=str(exp.get("type", "answer")),
                    must_include=list(exp.get("must_include", []) or []),
                    must_not_include=list(exp.get("must_not_include", []) or []),
                ),
            )
        )
    return cases


def eval_case(answer: str, fallback: bool, exp: Expected) -> Tuple[bool, List[str]]:
    ok = True
    reasons: List[str] = []
    exp_type = exp.type.lower().strip()
    if exp_type == "fallback":
        if not fallback:
            ok = False
            reasons.append("expected fallback=true")
    else:
        if fallback:
            ok = False
            reasons.append("unexpected fallback=true for answer case")

    ans_norm = (answer or "")
    for s in exp.must_include:
        if s and s not in ans_norm:
            ok = False
            reasons.append(f"missing include: {s}")
    for s in exp.must_not_include:
        if s and s in ans_norm:
            ok = False
            reasons.append(f"should not include: {s}")
    return ok, reasons


def run(base_url: str, cases: List[Case], timeout: float) -> int:
    client = httpx.Client(base_url=base_url, timeout=timeout)
    passed = 0
    total = 0
    start = time.time()
    print(f"Running {len(cases)} cases against {base_url}\n")
    for c in cases:
        total += 1
        try:
            resp = client.post("/ask", json={"question": c.question})
        except Exception as e:
            print(f"[FAIL] {c.name}: request error: {e}")
            continue
        if resp.status_code != 200:
            print(f"[FAIL] {c.name}: HTTP {resp.status_code}: {resp.text}")
            continue
        try:
            payload = resp.json()
        except json.JSONDecodeError:
            print(f"[FAIL] {c.name}: invalid JSON response: {resp.text[:200]}")
            continue
        answer = str(payload.get("answer", ""))
        fallback = bool(payload.get("fallback", False))
        ok, reasons = eval_case(answer, fallback, c.expected)
        if ok:
            print(f"[PASS] {c.name}")
            passed += 1
        else:
            print(f"[FAIL] {c.name}: {'; '.join(reasons)}")
            # Optional: show snippet
            if answer:
                snip = answer.replace("\n", " ")
                print(f"       answer: {snip[:160]}")
    dur = time.time() - start
    print(f"\nResult: {passed}/{total} passed in {dur:.2f}s")
    return 0 if passed == total else 1


def main():
    ap = argparse.ArgumentParser(description="Run acceptance tests against /ask API")
    ap.add_argument("--file", default="docs/acceptance_test.yml", help="Path to acceptance test YAML")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of API, e.g., http://localhost:8000")
    ap.add_argument("--timeout", type=float, default=30.0, help="Request timeout seconds")
    args = ap.parse_args()

    f = Path(args.file)
    if not f.exists():
        print(f"File not found: {f}", file=sys.stderr)
        sys.exit(2)
    cases = load_cases(f)
    if not cases:
        print("No cases found in YAML", file=sys.stderr)
        sys.exit(2)
    code = run(args.base_url, cases, args.timeout)
    sys.exit(code)


if __name__ == "__main__":
    main()

