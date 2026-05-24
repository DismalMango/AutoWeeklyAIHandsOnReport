from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "ai-product-report"


def extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return "AI Product Report"


def ensure_public_research_disclaimer(markdown: str) -> str:
    disclaimer = (
        "> 说明：本报告基于公开网页、文档、演示和第三方评价生成，"
        "不代表已经完成真实账号注册、登录或付费试用。"
    )
    if "本报告基于公开网页" in markdown:
        return markdown
    return f"{disclaimer}\n\n{markdown.strip()}\n"


def strip_preamble(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            return "\n".join(lines[index:]).strip()
    return markdown.strip()


def write_report(markdown: str, output_dir: Path, report_date: date) -> Path:
    final_markdown = ensure_public_research_disclaimer(strip_preamble(markdown))
    title = extract_title(final_markdown)
    dated_dir = output_dir / report_date.isoformat()
    dated_dir.mkdir(parents=True, exist_ok=True)
    path = dated_dir / f"{slugify(title)}.md"
    path.write_text(final_markdown, encoding="utf-8")
    return path
