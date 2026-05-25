from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Callable, cast

from langchain_core.language_models import BaseChatModel
from langchain_tavily import TavilyExtract, TavilySearch
from pydantic import BaseModel, Field

from ..reporting import slugify
from .state import CandidateProduct, GraphState, SelectionOption, SourceRef


class SearchCandidateModel(BaseModel):
    name: str
    summary: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    recent_signals: list[str] = Field(default_factory=list)
    evidence_notes: list[str] = Field(default_factory=list)
    confidence: str


class SearchCandidatesOutput(BaseModel):
    candidates: list[SearchCandidateModel]


class SelectionOptionModel(BaseModel):
    slug: str
    score: float
    rationale: str
    tradeoffs: list[str] = Field(default_factory=list)


class SelectProductOutput(BaseModel):
    recommended_slug: str
    options: list[SelectionOptionModel]


class ReviewOutput(BaseModel):
    report_markdown: str


def _format_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _normalize_candidate(candidate: SearchCandidateModel) -> CandidateProduct:
    return {
        "name": candidate.name,
        "slug": slugify(candidate.name),
        "summary": candidate.summary,
        "source_refs": candidate.source_refs,
        "recent_signals": candidate.recent_signals,
        "evidence_notes": candidate.evidence_notes,
        "confidence": candidate.confidence,
    }


def _compute_date_range(state: GraphState) -> tuple[str | None, str | None]:
    today_text = state.get("today")
    if not today_text:
        return None, None
    today_value = date.fromisoformat(today_text)
    days = state.get("days", 30)
    start_date = today_value - timedelta(days=max(days - 1, 0))
    return start_date.isoformat(), today_value.isoformat()


def create_search_candidates_node(
    model: BaseChatModel,
    search_tool: TavilySearch,
    extract_tool: TavilyExtract,
) -> Callable[[GraphState], GraphState]:
    structured_model = model.with_structured_output(
        SearchCandidatesOutput,
        method="function_calling",
    )

    def search_candidates(state: GraphState) -> GraphState:
        topic = state.get("topic", "general")
        days = state.get("days", 30)
        start_date, end_date = _compute_date_range(state)
        query = (
            f"recent AI native products {topic} launched updated reviewed in the last {days} days"
        )
        search_results = search_tool.invoke(
            {
                "query": query,
                "search_depth": "advanced",
                "topic": "general",
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        result_items = search_results.get("results", []) if isinstance(search_results, dict) else []
        urls = [item.get("url") for item in result_items if isinstance(item, dict) and item.get("url")]
        extract_results: dict[str, Any] = {"results": []}
        if urls:
            extract_results = cast(
                dict[str, Any],
                extract_tool.invoke(
                    {
                        "urls": urls[: state.get("max_candidates", 8)],
                        "extract_depth": "advanced",
                        "query": "product overview, launch details, target users, usage flow",
                    }
                ),
            )

        prompt = f"""You are structuring candidate AI products from public research.

Today: {state.get("today")}
Time window: last {days} days
Topic hint: {topic}
Max candidates: {state.get("max_candidates", 8)}

Search results:
{_format_json(search_results)}

Extracted content:
{_format_json(extract_results)}

Return 2 to {state.get("max_candidates", 8)} AI-native product candidates.
Only include products with enough evidence for later evaluation.
For each candidate, keep source_refs diverse when possible.
"""
        output = structured_model.invoke(prompt)
        candidates = [_normalize_candidate(candidate) for candidate in output.candidates]
        if not candidates:
            raise ValueError("No candidate products found from search results.")
        return {"candidates": candidates}

    return search_candidates


def create_select_product_node(model: BaseChatModel) -> Callable[[GraphState], GraphState]:
    structured_model = model.with_structured_output(
        SelectProductOutput,
        method="function_calling",
    )

    def select_product(state: GraphState) -> GraphState:
        prompt = f"""You are selecting AI-native product candidates for a report.

Selection criteria:
- recency of launch, update, or discussion signals
- strength of AI-native positioning
- clarity of target user and usage scenario
- completeness and diversity of public evidence
- likely value of the product as a report subject

Candidates:
{_format_json(state.get("candidates", []))}

Return 2 to 4 options. Recommend exactly one slug from the provided candidates.
Keep rationale concise and make tradeoffs explicit.
"""
        output = structured_model.invoke(prompt)
        options: list[SelectionOption] = [
            {
                "slug": option.slug,
                "score": option.score,
                "rationale": option.rationale,
                "tradeoffs": option.tradeoffs,
            }
            for option in output.options
        ]
        candidate_slugs = {candidate["slug"] for candidate in state.get("candidates", [])}
        option_slugs = {option["slug"] for option in options}
        if not option_slugs.issubset(candidate_slugs):
            raise ValueError("Selection options must refer to known candidate slugs.")
        if output.recommended_slug not in option_slugs:
            raise ValueError("Recommended slug must appear in selection options.")
        return {
            "selection": {
                "recommended_slug": output.recommended_slug,
                "options": options,
            }
        }

    return select_product


def resolve_selection(state: GraphState) -> GraphState:
    selection = dict(state.get("selection", {}))
    options = selection.get("options", [])
    option_slugs = {option["slug"] for option in options}
    chosen_slug = selection.get("user_selected_slug") or selection.get("recommended_slug")
    if not chosen_slug or chosen_slug not in option_slugs:
        raise ValueError(f"Invalid selected slug: {chosen_slug}")

    matched_option = next(option for option in options if option["slug"] == chosen_slug)
    selection["final_slug"] = chosen_slug
    selection["decision_mode"] = "user" if selection.get("user_selected_slug") else "auto"
    selection["final_rationale"] = matched_option["rationale"]
    return {"selection": selection}


def create_write_editorial_review_node(
    model: BaseChatModel,
) -> Callable[[GraphState], GraphState]:
    structured_model = model.with_structured_output(
        ReviewOutput,
        method="function_calling",
    )

    def write_editorial_review(state: GraphState) -> GraphState:
        final_slug = state.get("selection", {}).get("final_slug")
        candidates = state.get("candidates", [])
        candidate = next((item for item in candidates if item["slug"] == final_slug), None)
        if candidate is None:
            raise ValueError(f"Selected candidate not found: {final_slug}")

        prompt = f"""Write a Chinese editorial-style AI product review based only on public information.

Requirements:
- make it clear this is based on public research, not real account usage
- focus on positioning, experience framing, strengths, limitations, and who it fits
- include visible source links
- output Markdown only

Selected candidate:
{_format_json(candidate)}

Selection summary:
{_format_json(state.get("selection", {}))}
"""
        output = structured_model.invoke(prompt)
        return {"report_markdown": output.report_markdown}

    return write_editorial_review
