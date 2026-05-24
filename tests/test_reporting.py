from datetime import date

from auto_weekly_ai_feedback.reporting import (
    ensure_public_research_disclaimer,
    slugify,
    strip_preamble,
    write_report,
)


def test_slugify_falls_back_for_non_ascii_title() -> None:
    assert slugify("产品名：一句话定位") == "ai-product-report"


def test_disclaimer_is_added_once() -> None:
    markdown = "# Test\n\nBody"
    first = ensure_public_research_disclaimer(markdown)
    second = ensure_public_research_disclaimer(first)

    assert first == second
    assert "本报告基于公开网页" in first


def test_write_report_creates_dated_markdown(tmp_path) -> None:
    path = write_report("# Example Product: AI helper\n\nBody", tmp_path, date(2026, 5, 24))

    assert path.name == "example-product-ai-helper.md"
    assert path.exists()
    assert "本报告基于公开网页" in path.read_text(encoding="utf-8")


def test_strip_preamble_keeps_first_h1() -> None:
    markdown = "现在我已经获得资料。\n\n---\n\n# Product\n\nBody"

    assert strip_preamble(markdown) == "# Product\n\nBody"
