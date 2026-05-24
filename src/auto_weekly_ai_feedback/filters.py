from __future__ import annotations

from urllib.parse import urlparse

from .models import ProductCandidate


AI_NATIVE_TERMS = (
    "agent",
    "ai agent",
    "copilot",
    "llm",
    "model",
    "prompt",
    "workflow",
    "automation",
    "生成式",
    "智能体",
    "大模型",
)


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{netloc}{path}"


def dedupe_candidates(candidates: list[ProductCandidate]) -> list[ProductCandidate]:
    seen: set[str] = set()
    unique: list[ProductCandidate] = []

    for candidate in candidates:
        key = normalize_url(str(candidate.url)) or candidate.name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)

    return unique


def looks_ai_native(candidate: ProductCandidate) -> bool:
    text = " ".join(
        [
            candidate.name,
            candidate.description,
            candidate.recency_signal,
            candidate.ai_native_reason,
        ]
    ).lower()
    return any(term in text for term in AI_NATIVE_TERMS)
