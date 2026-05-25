from __future__ import annotations

from typing import Literal, TypedDict


class SourceRef(TypedDict):
    title: str
    url: str
    source_type: str


class CandidateProduct(TypedDict):
    name: str
    slug: str
    summary: str
    source_refs: list[SourceRef]
    recent_signals: list[str]
    evidence_notes: list[str]
    confidence: str


class SelectionOption(TypedDict):
    slug: str
    score: float
    rationale: str
    tradeoffs: list[str]


class SelectionDecision(TypedDict, total=False):
    recommended_slug: str
    options: list[SelectionOption]
    user_selected_slug: str
    final_slug: str
    decision_mode: Literal["auto", "user"]
    final_rationale: str


class GraphState(TypedDict, total=False):
    today: str
    days: int
    topic: str
    max_candidates: int
    candidates: list[CandidateProduct]
    selection: SelectionDecision
    report_markdown: str
    errors: list[str]
