from auto_weekly_ai_feedback.filters import dedupe_candidates, looks_ai_native
from auto_weekly_ai_feedback.models import ProductCandidate


def test_dedupe_candidates_by_normalized_url() -> None:
    candidates = [
        ProductCandidate(name="A", url="https://www.example.com/product/"),
        ProductCandidate(name="A copy", url="https://example.com/product"),
    ]

    assert len(dedupe_candidates(candidates)) == 1


def test_looks_ai_native_uses_core_terms() -> None:
    candidate = ProductCandidate(
        name="Workflow Agent",
        url="https://example.com",
        description="An AI agent for automating research workflows.",
    )

    assert looks_ai_native(candidate)
