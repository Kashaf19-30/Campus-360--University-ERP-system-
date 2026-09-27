#!/usr/bin/env python3
"""Count lines of code in Campus360 project."""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

ROOTS = [Path(r"D:/cmp/Campus360"), Path(r"D:/cmp/docs/campus360")]
EXCLUDE_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    "media", ".git", "diagrams", ".pytest_cache", "htmlcov",
}
CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".html", ".htm"}
DOC_EXTS = {".md", ".json", ".yml", ".yaml"}
SKIP_FILES = {"package-lock.json"}


def scan(root: Path) -> tuple[dict, dict, dict, dict]:
    code: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0})
    docs: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0})
    backend_py = frontend_js = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            p = Path(dirpath) / fn
            ext = p.suffix.lower()
            if ext not in CODE_EXTS and ext not in DOC_EXTS:
                continue
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except OSError:
                continue

            rel = str(p.relative_to(root)).replace("\\", "/")
            bucket = code if ext in CODE_EXTS else docs
            bucket[ext]["files"] += 1
            bucket[ext]["lines"] += lines

            if ext == ".py" and "backend" in rel.split("/"):
                backend_py += lines
            if ext in {".js", ".jsx"} and "Frontend" in rel:
                frontend_js += lines

    return code, docs, {"backend_py": backend_py}, {"frontend_js": frontend_js}


def breakdown_campus360(root: Path) -> None:
    cats: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0})
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith(tuple(CODE_EXTS)):
                continue
            p = Path(dirpath) / fn
            rel = p.relative_to(root).as_posix()
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except OSError:
                continue
            if "/migrations/" in rel:
                cat = "migrations"
            elif "/tests/" in rel or fn.startswith("test_") or ".test." in fn:
                cat = "tests"
            elif rel.startswith("backend/") and fn.endswith(".py"):
                cat = "backend_app"
            elif rel.startswith("Frontend/"):
                cat = "frontend"
            else:
                cat = "other"
            cats[cat]["files"] += 1
            cats[cat]["lines"] += lines

    print("\n--- Breakdown (Campus360 app) ---")
    for cat in ("backend_app", "frontend", "tests", "migrations", "other"):
        v = cats[cat]
        print(f"  {cat:14} {v['files']:4} files  {v['lines']:7,} lines")
    app = cats["backend_app"]["lines"] + cats["frontend"]["lines"]
    print(f"  Application code (backend + frontend): {app:,} lines")
    print(f"  Excluding tests & migrations: {app:,} lines")


def main() -> None:
    grand_code: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0})
    grand_docs: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0})
    be_total = fe_total = 0

    for root in ROOTS:
        if not root.exists():
            print(f"Missing: {root}")
            continue
        code, docs, be, fe = scan(root)
        code_lines = sum(v["lines"] for v in code.values())
        code_files = sum(v["files"] for v in code.values())
        doc_lines = sum(v["lines"] for v in docs.values())

        print(f"\n=== {root} ===")
        print(f"Source code: {code_files:,} files, {code_lines:,} lines")
        for ext, v in sorted(code.items(), key=lambda x: -x[1]["lines"]):
            print(f"  {ext:5} {v['lines']:>7,} lines  ({v['files']} files)")

        if docs:
            print(f"Docs/config: {sum(v['files'] for v in docs.values())} files, {doc_lines:,} lines")

        if root.name == "Campus360":
            be_total = be["backend_py"]
            fe_total = fe["frontend_js"]
            print(f"  Backend Python (.py under backend/): {be_total:,}")
            print(f"  Frontend JS/JSX (under Frontend/): {fe_total:,}")

        for bucket, target in ((code, grand_code), (docs, grand_docs)):
            for ext, v in bucket.items():
                target[ext]["files"] += v["files"]
                target[ext]["lines"] += v["lines"]

    total_code = sum(v["lines"] for v in grand_code.values())
    total_docs = sum(v["lines"] for v in grand_docs.values())
    total_files = sum(v["files"] for v in grand_code.values()) + sum(v["files"] for v in grand_docs.values())

    print("\n=== SUMMARY ===")
    print(f"Application source code:     {sum(v['files'] for v in grand_code.values()):,} files, {total_code:,} lines")
    print(f"  Python (.py):              {grand_code['.py']['lines']:,}")
    print(f"  JavaScript/JSX:            {grand_code['.js']['lines'] + grand_code['.jsx']['lines']:,}")
    print(f"  CSS:                       {grand_code['.css']['lines']:,}")
    print(f"  HTML:                      {grand_code['.html']['lines']:,}")
    print(f"Documentation (docs/*.md):   {grand_docs['.md']['lines']:,} lines in {grand_docs['.md']['files']} files")
    print(f"Grand total (code + docs):   {total_files:,} files, {total_code + total_docs:,} lines")
    breakdown_campus360(Path(r"D:/cmp/Campus360"))


if __name__ == "__main__":
    main()
