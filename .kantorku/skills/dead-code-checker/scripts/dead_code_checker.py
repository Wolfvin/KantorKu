#!/usr/bin/env python3
"""Dead code / unwired code checker.

Usage examples:
  python scripts/dead_code_checker.py --from-git-diff
  python scripts/dead_code_checker.py --token class:setup-card-sm --token id:rek-doc-top-bni
  python scripts/dead_code_checker.py --from-git-diff --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

TOKEN_TYPES = {"class", "id", "symbol"}
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "target",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".next",
}

HTML_EXT = {".html", ".htm", ".xhtml"}
CSS_EXT = {".css", ".scss", ".sass", ".less"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
CODE_EXT = HTML_EXT | CSS_EXT | JS_EXT | {
    ".py",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".php",
    ".rb",
    ".cs",
    ".cpp",
    ".c",
    ".h",
}


@dataclass(frozen=True)
class Token:
    kind: str
    name: str


@dataclass
class Occurrence:
    path: str
    line: int
    role: str
    text: str


@dataclass
class Analysis:
    token: Token
    status: str
    verdict: str
    recommendation: str
    occurrences: List[Occurrence]


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _iter_files(root: Path) -> Iterable[Path]:
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        base_path = Path(base)
        for name in files:
            p = base_path / name
            if p.suffix.lower() in CODE_EXT:
                yield p


def parse_token_spec(spec: str) -> Token:
    if ":" not in spec:
        raise ValueError(f"Invalid token '{spec}'. Use <class|id|symbol>:<name>.")
    kind, name = spec.split(":", 1)
    kind = kind.strip().lower()
    name = name.strip()
    if kind not in TOKEN_TYPES:
        raise ValueError(f"Invalid token kind '{kind}' in '{spec}'.")
    if not name:
        raise ValueError(f"Empty token name in '{spec}'.")
    return Token(kind=kind, name=name)


def _extract_tokens_from_removed_line(line: str) -> Set[Token]:
    found: Set[Token] = set()

    for classes in re.findall(r'class\s*=\s*["\']([^"\']+)["\']', line):
        for c in re.split(r"\s+", classes.strip()):
            if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", c):
                found.add(Token("class", c))

    for ident in re.findall(r'id\s*=\s*["\']([A-Za-z_][A-Za-z0-9_-]*)["\']', line):
        found.add(Token("id", ident))

    for c in re.findall(r'(?<![\w-])\.([A-Za-z_][A-Za-z0-9_-]*)', line):
        found.add(Token("class", c))
    for i in re.findall(r'(?<![\w-])#([A-Za-z_][A-Za-z0-9_-]*)', line):
        found.add(Token("id", i))

    for sel_kind, sel_name in re.findall(r'querySelector(?:All)?\(\s*["\']([.#])([A-Za-z_][A-Za-z0-9_-]*)["\']', line):
        found.add(Token("class" if sel_kind == "." else "id", sel_name))

    for ident in re.findall(r'getElementById\(\s*["\']([A-Za-z_][A-Za-z0-9_-]*)["\']', line):
        found.add(Token("id", ident))

    for ident in re.findall(r'getElementsByClassName\(\s*["\']([A-Za-z_][A-Za-z0-9_-]*)["\']', line):
        found.add(Token("class", ident))

    for ident in re.findall(r'classList\.(?:add|remove|toggle|contains)\(\s*["\']([A-Za-z_][A-Za-z0-9_-]*)["\']', line):
        found.add(Token("class", ident))

    for ident in re.findall(r'\b(?:function|class|fn|def|struct|enum|impl)\s+([A-Za-z_][A-Za-z0-9_]*)', line):
        found.add(Token("symbol", ident))

    return found


def tokens_from_git_diff(root: Path) -> Set[Token]:
    cmd = ["git", "diff", "--unified=0", "--", str(root)]
    try:
        out = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=root,
        )
    except OSError:
        return set()

    text = out.stdout or ""
    tokens: Set[Token] = set()
    for line in text.splitlines():
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if not line.startswith("-"):
            continue
        removed = line[1:]
        tokens.update(_extract_tokens_from_removed_line(removed))
    return tokens


def _roles_for_line(token: Token, line: str, ext: str) -> List[str]:
    roles: List[str] = []
    name = re.escape(token.name)

    if token.kind == "class":
        if ext in HTML_EXT and re.search(r'class\s*=\s*["\'][^"\']*\b' + name + r'\b', line):
            roles.append("html-declaration")
        if ext in CSS_EXT and re.search(r'(?<![\w-])\.' + name + r'(?![\w-])', line):
            roles.append("css-selector")
        if ext in JS_EXT and (
            re.search(r'querySelector(?:All)?\(\s*["\']\.' + name + r'["\']', line)
            or re.search(r'getElementsByClassName\(\s*["\']' + name + r'["\']', line)
            or re.search(r'classList\.(?:add|remove|toggle|contains)\(\s*["\']' + name + r'["\']', line)
        ):
            roles.append("js-selector")

    elif token.kind == "id":
        if ext in HTML_EXT and re.search(r'id\s*=\s*["\']' + name + r'["\']', line):
            roles.append("html-declaration")
        if ext in CSS_EXT and re.search(r'(?<![\w-])#' + name + r'(?![\w-])', line):
            roles.append("css-selector")
        if ext in JS_EXT and (
            re.search(r'getElementById\(\s*["\']' + name + r'["\']', line)
            or re.search(r'querySelector(?:All)?\(\s*["\']#' + name + r'["\']', line)
        ):
            roles.append("js-selector")

    else:  # symbol
        if re.search(r'\b' + name + r'\b', line):
            if ext in HTML_EXT:
                roles.append("html-reference")
            elif ext in JS_EXT:
                roles.append("js-reference")
            elif ext in CSS_EXT:
                roles.append("css-reference")
            else:
                roles.append("backend-reference")

    if not roles and re.search(r'\b' + name + r'\b', line):
        if ext in HTML_EXT:
            roles.append("html-reference")
        elif ext in CSS_EXT:
            roles.append("css-reference")
        elif ext in JS_EXT:
            roles.append("js-reference")
        else:
            roles.append("backend-reference")

    return roles


def collect_occurrences(root: Path, token: Token) -> List[Occurrence]:
    hits: List[Occurrence] = []
    for file_path in _iter_files(root):
        ext = file_path.suffix.lower()
        text = _safe_read(file_path)
        for idx, line in enumerate(text.splitlines(), start=1):
            roles = _roles_for_line(token, line, ext)
            for role in roles:
                hits.append(
                    Occurrence(
                        path=str(file_path.relative_to(root)).replace("\\", "/"),
                        line=idx,
                        role=role,
                        text=line.strip()[:220],
                    )
                )
    return hits


def classify(token: Token, occurrences: List[Occurrence]) -> Tuple[str, str, str]:
    roles = {o.role for o in occurrences}
    has_html = any(r.startswith("html-") for r in roles)
    has_css = any(r.startswith("css-") for r in roles)
    has_js = any(r.startswith("js-") for r in roles)
    has_backend = any(r.startswith("backend-") for r in roles)

    if token.kind in {"class", "id"}:
        if not has_html:
            return (
                "is dead code",
                "unwired-to-html",
                "delete or wire to html",
            )
        if has_css or has_js:
            return (
                "is not dead code",
                "wired",
                "keep (or refactor carefully)",
            )
        return (
            "is not dead code",
            "legacy-html-only",
            "legacy: verify if style/script wiring still needed",
        )

    # symbol mode (more aggressive policy requested)
    if has_html or has_js or has_css:
        return (
            "is not dead code",
            "wired-via-frontend",
            "keep (frontend still references symbol)",
        )
    if has_backend:
        return (
            "is dead code",
            "backend-unwired-to-html",
            "wire? delete? more-advance? legacy?",
        )
    return (
        "is dead code",
        "not-found",
        "delete",
    )


def run(root: Path, tokens: Iterable[Token]) -> List[Analysis]:
    result: List[Analysis] = []
    for token in sorted(set(tokens), key=lambda t: (t.kind, t.name)):
        occurrences = collect_occurrences(root, token)
        status, verdict, recommendation = classify(token, occurrences)
        result.append(
            Analysis(
                token=token,
                status=status,
                verdict=verdict,
                recommendation=recommendation,
                occurrences=occurrences,
            )
        )
    return result


def print_text_report(analyses: List[Analysis]) -> None:
    if not analyses:
        print("No tokens to analyze.")
        return

    for item in analyses:
        print(f"Token: {item.token.kind}:{item.token.name}")
        print(f"Status: {item.status}")
        print(f"Verdict: {item.verdict}")
        print(f"Recommendation: {item.recommendation}")
        if not item.occurrences:
            print("Occurrences:")
            print("- path: (none)")
            print("  line: (none)")
            print("  role: (none)")
        else:
            print("Occurrences:")
            for occ in item.occurrences:
                print(f"- path: {occ.path}")
                print(f"  line: {occ.line}")
                print(f"  role: {occ.role}")
        print("---")


def to_json_ready(analyses: List[Analysis]) -> List[Dict[str, object]]:
    out = []
    for item in analyses:
        out.append(
            {
                "token": {"kind": item.token.kind, "name": item.token.name},
                "status": item.status,
                "verdict": item.verdict,
                "recommendation": item.recommendation,
                "occurrences": [
                    {
                        "path": o.path,
                        "line": o.line,
                        "role": o.role,
                        "text": o.text,
                    }
                    for o in item.occurrences
                ],
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Dead code / unwired code checker")
    parser.add_argument("--root", default=".", help="Project root (default: current directory)")
    parser.add_argument("--token", action="append", default=[], help="Token in format class:name / id:name / symbol:name")
    parser.add_argument("--from-git-diff", action="store_true", help="Extract removed tokens from git diff")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root not found: {root}")
        return 2

    tokens: Set[Token] = set()
    for spec in args.token:
        try:
            tokens.add(parse_token_spec(spec))
        except ValueError as err:
            print(f"Error: {err}")
            return 2

    if args.from_git_diff:
        tokens.update(tokens_from_git_diff(root))

    analyses = run(root, tokens)

    if args.json:
        print(json.dumps(to_json_ready(analyses), indent=2))
    else:
        print_text_report(analyses)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
