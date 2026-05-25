from __future__ import annotations

from typing import Callable

from langgraph.graph import END, START, StateGraph

from ..agent import build_default_nodes
from ..config import Settings
from .nodes import resolve_selection
from .state import GraphState


NodeFn = Callable[[GraphState], GraphState]


def _merge_state(base: GraphState, update: GraphState) -> GraphState:
    merged = dict(base)
    for key, value in update.items():
        if key == "selection":
            merged["selection"] = {**merged.get("selection", {}), **value}
        else:
            merged[key] = value
    return merged


def _wrap_node(node_fn: NodeFn) -> NodeFn:
    def wrapped(state: GraphState) -> GraphState:
        return _merge_state(state, node_fn(state))

    return wrapped


def build_workflow(
    *,
    search_candidates_fn: NodeFn,
    select_product_fn: NodeFn,
    write_editorial_review_fn: NodeFn,
):
    graph = StateGraph(GraphState)
    graph.add_node("search_candidates", _wrap_node(search_candidates_fn))
    graph.add_node("select_product", _wrap_node(select_product_fn))
    graph.add_node("resolve_selection", _wrap_node(resolve_selection))
    graph.add_node("write_editorial_review", _wrap_node(write_editorial_review_fn))
    graph.add_edge(START, "search_candidates")
    graph.add_edge("search_candidates", "select_product")
    graph.add_edge("select_product", "resolve_selection")
    graph.add_edge("resolve_selection", "write_editorial_review")
    graph.add_edge("write_editorial_review", END)
    return graph.compile()


def _resolve_nodes(
    *,
    settings: Settings | None,
    search_candidates_fn: NodeFn | None,
    select_product_fn: NodeFn | None,
    write_editorial_review_fn: NodeFn | None,
) -> tuple[NodeFn, NodeFn, NodeFn]:
    if search_candidates_fn and select_product_fn and write_editorial_review_fn:
        return search_candidates_fn, select_product_fn, write_editorial_review_fn
    if settings is None:
        raise ValueError("Settings are required when node functions are not provided.")
    default_search, default_select, default_write = build_default_nodes(settings)
    return (
        search_candidates_fn or default_search,
        select_product_fn or default_select,
        write_editorial_review_fn or default_write,
    )


def run_until_selection(
    *,
    initial_state: GraphState,
    settings: Settings | None = None,
    search_candidates_fn: NodeFn | None = None,
    select_product_fn: NodeFn | None = None,
    write_editorial_review_fn: NodeFn | None = None,
) -> GraphState:
    search_node, select_node, write_node = _resolve_nodes(
        settings=settings,
        search_candidates_fn=search_candidates_fn,
        select_product_fn=select_product_fn,
        write_editorial_review_fn=write_editorial_review_fn or (lambda state: state),
    )
    workflow = build_workflow(
        search_candidates_fn=search_node,
        select_product_fn=select_node,
        write_editorial_review_fn=write_node,
    )
    return workflow.invoke(initial_state, interrupt_before=["resolve_selection"])


def run_workflow(
    *,
    initial_state: GraphState,
    settings: Settings | None = None,
    search_candidates_fn: NodeFn | None = None,
    select_product_fn: NodeFn | None = None,
    write_editorial_review_fn: NodeFn | None = None,
    user_selected_slug: str | None = None,
) -> GraphState:
    effective_state = dict(initial_state)
    if user_selected_slug:
        effective_state["selection"] = {
            **effective_state.get("selection", {}),
            "user_selected_slug": user_selected_slug,
        }

    search_node, select_node, write_node = _resolve_nodes(
        settings=settings,
        search_candidates_fn=search_candidates_fn,
        select_product_fn=select_product_fn,
        write_editorial_review_fn=write_editorial_review_fn,
    )
    workflow = build_workflow(
        search_candidates_fn=search_node,
        select_product_fn=select_node,
        write_editorial_review_fn=write_node,
    )
    return workflow.invoke(effective_state)
