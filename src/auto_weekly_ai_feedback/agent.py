from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langchain_tavily import TavilyExtract, TavilySearch

from .config import Settings
from .graph.nodes import (
    create_search_candidates_node,
    create_select_product_node,
    create_write_editorial_review_node,
)


def build_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=90,
        extra_body={"thinking": {"type": "disabled"}},
    )


def build_tools(settings: Settings) -> tuple[TavilySearch, TavilyExtract]:
    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
    return (
        TavilySearch(max_results=10, topic="general"),
        TavilyExtract(),
    )


def build_default_nodes(settings: Settings):
    model = build_model(settings)
    search_tool, extract_tool = build_tools(settings)
    return (
        create_search_candidates_node(model, search_tool, extract_tool),
        create_select_product_node(model),
        create_write_editorial_review_node(model),
    )
