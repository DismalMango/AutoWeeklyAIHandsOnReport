from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from auto_weekly_ai_feedback.cli import app
from auto_weekly_ai_feedback.graph.nodes import (
    _format_json,
    create_search_candidates_node,
    create_select_product_node,
    create_write_editorial_review_node,
    resolve_selection,
)
from auto_weekly_ai_feedback.graph.state import CandidateProduct, GraphState
from auto_weekly_ai_feedback.graph.workflow import run_until_selection, run_workflow


def make_candidate(slug: str) -> CandidateProduct:
    return {
        "name": slug.replace("-", " ").title(),
        "slug": slug,
        "summary": f"{slug} summary",
        "source_refs": [
            {
                "title": f"{slug} official",
                "url": f"https://{slug}.example.com",
                "source_type": "official",
            }
        ],
        "recent_signals": [f"{slug} launched recently"],
        "evidence_notes": [f"{slug} evidence"],
        "confidence": "medium",
    }


def make_selection_state() -> GraphState:
    return {
        "selection": {
            "recommended_slug": "product-a",
            "options": [
                {
                    "slug": "product-a",
                    "score": 9.2,
                    "rationale": "best evidence",
                    "tradeoffs": ["narrow audience"],
                },
                {
                    "slug": "product-b",
                    "score": 8.4,
                    "rationale": "good but less current",
                    "tradeoffs": ["lighter source coverage"],
                },
            ],
        }
    }


def test_resolve_selection_prefers_recommendation_when_no_user_choice() -> None:
    result = resolve_selection(make_selection_state())

    assert result["selection"]["final_slug"] == "product-a"
    assert result["selection"]["decision_mode"] == "auto"
    assert result["selection"]["final_rationale"] == "best evidence"


def test_run_workflow_uses_user_selected_slug_in_user_mode() -> None:
    initial_state: GraphState = {
        "today": "2026-05-25",
        "days": 30,
        "topic": "general",
        "max_candidates": 4,
    }

    final_state = run_workflow(
        initial_state=initial_state,
        search_candidates_fn=lambda state: {
            "candidates": [make_candidate("product-a"), make_candidate("product-b")]
        },
        select_product_fn=lambda state: {
            "selection": make_selection_state()["selection"]
        },
        write_editorial_review_fn=lambda state: {
            "report_markdown": f"# {state['selection']['final_slug']}\n\nBody"
        },
        user_selected_slug="product-b",
    )

    assert final_state["selection"]["final_slug"] == "product-b"
    assert final_state["selection"]["decision_mode"] == "user"
    assert final_state["report_markdown"].startswith("# product-b")


def test_run_until_selection_returns_options_without_report() -> None:
    initial_state: GraphState = {
        "today": "2026-05-25",
        "days": 30,
        "topic": "general",
        "max_candidates": 4,
    }

    state = run_until_selection(
        initial_state=initial_state,
        search_candidates_fn=lambda state: {
            "candidates": [make_candidate("product-a"), make_candidate("product-b")]
        },
        select_product_fn=lambda state: {
            "selection": make_selection_state()["selection"]
        },
    )

    assert state["selection"]["recommended_slug"] == "product-a"
    assert len(state["selection"]["options"]) == 2
    assert "report_markdown" not in state


def test_run_workflow_rejects_unknown_user_selected_slug() -> None:
    initial_state: GraphState = {
        "today": "2026-05-25",
        "days": 30,
        "topic": "general",
        "max_candidates": 4,
    }

    with pytest.raises(ValueError, match="Invalid selected slug"):
        run_workflow(
            initial_state=initial_state,
            search_candidates_fn=lambda state: {"candidates": [make_candidate("product-a")]},
            select_product_fn=lambda state: {
                "selection": make_selection_state()["selection"]
            },
            write_editorial_review_fn=lambda state: {"report_markdown": "# product-a\n\nBody"},
            user_selected_slug="missing-slug",
        )


def test_cli_run_prompts_for_slug_in_user_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import auto_weekly_ai_feedback.cli as cli_module

    class DummySettings:
        pass

    captured: dict[str, str] = {}

    def fake_run_until_selection(*, initial_state: GraphState, **_: object) -> GraphState:
        captured["topic"] = initial_state["topic"]
        return {
            **initial_state,
            "candidates": [make_candidate("product-a"), make_candidate("product-b")],
            "selection": make_selection_state()["selection"],
        }

    def fake_run_workflow(
        *,
        initial_state: GraphState,
        user_selected_slug: str | None = None,
        **_: object,
    ) -> GraphState:
        captured["selected_slug"] = user_selected_slug or ""
        return {
            **initial_state,
            "selection": {
                **make_selection_state()["selection"],
                "final_slug": user_selected_slug or "product-a",
                "decision_mode": "user" if user_selected_slug else "auto",
                "final_rationale": "chosen",
            },
            "report_markdown": "# product-b\n\nBody",
        }

    def fake_write_report(markdown: str, output_dir: Path, report_date) -> Path:
        path = output_dir / report_date.isoformat() / "product-b.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        return path

    monkeypatch.setattr(cli_module.Settings, "from_env", classmethod(lambda cls: DummySettings()))
    monkeypatch.setattr(cli_module, "run_until_selection", fake_run_until_selection)
    monkeypatch.setattr(cli_module, "run_workflow", fake_run_workflow)
    monkeypatch.setattr(cli_module, "write_report", fake_write_report)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--selection-mode",
            "user",
            "--output",
            str(tmp_path),
            "--topic",
            "agents",
        ],
        input="product-b\n",
    )

    assert result.exit_code == 0
    assert captured == {"topic": "agents", "selected_slug": "product-b"}
    assert "product-a" in result.stdout
    assert "product-b" in result.stdout


def test_format_json_handles_connection_error_objects() -> None:
    rendered = _format_json({"error": ConnectionError("dns failed")})

    assert "dns failed" in rendered


def test_nodes_use_function_calling_structured_output() -> None:
    class DummyModel:
        def __init__(self) -> None:
            self.calls: list[tuple[object, str]] = []

        def with_structured_output(self, schema, *, method="json_schema", **kwargs):
            self.calls.append((schema, method))

            class DummyRunnable:
                def invoke(self, prompt):
                    raise AssertionError("invoke should not be called in this test")

            return DummyRunnable()

    class DummyTool:
        def invoke(self, payload):
            raise AssertionError("invoke should not be called in this test")

    model = DummyModel()
    create_search_candidates_node(model, DummyTool(), DummyTool())
    create_select_product_node(model)
    create_write_editorial_review_node(model)

    assert [method for _, method in model.calls] == [
        "function_calling",
        "function_calling",
        "function_calling",
    ]
