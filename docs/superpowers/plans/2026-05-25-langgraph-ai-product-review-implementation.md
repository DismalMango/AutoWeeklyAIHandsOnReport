# LangGraph AI Product Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the single-shot AI product report generator into a LangGraph workflow with candidate search, recommendation, selection resolution, and editorial review generation.

**Architecture:** Introduce a `graph` package that owns state, node contracts, and workflow assembly. Reuse the existing model and Tavily configuration as factories, keep report writing unchanged, and expose selection mode control through the CLI.

**Tech Stack:** Python 3.12, LangGraph, LangChain OpenAI, LangChain Tavily, Typer, Pytest

---

### Task 1: Add deterministic workflow tests first

**Files:**
- Create: `tests/test_workflow.py`
- Check: `src/auto_weekly_ai_feedback/cli.py`
- Check: `src/auto_weekly_ai_feedback/reporting.py`

- [ ] **Step 1: Write the failing tests**

```python
from auto_weekly_ai_feedback.graph.state import CandidateProduct, SelectionDecision
from auto_weekly_ai_feedback.graph.workflow import run_until_selection, run_workflow


def make_candidate(slug: str) -> CandidateProduct:
    return {
        "name": slug.title(),
        "slug": slug,
        "summary": f"{slug} summary",
        "source_refs": [{"title": slug, "url": f"https://{slug}.example.com", "source_type": "official"}],
        "recent_signals": [f"{slug} launched recently"],
        "evidence_notes": [f"{slug} evidence"],
        "confidence": "medium",
    }


def test_run_workflow_uses_recommended_slug_in_auto_mode() -> None:
    final_state = run_workflow(...)
    assert final_state["selection"]["final_slug"] == "product-a"


def test_run_workflow_uses_user_selected_slug_in_user_mode() -> None:
    final_state = run_workflow(...)
    assert final_state["selection"]["decision_mode"] == "user"
    assert final_state["selection"]["final_slug"] == "product-b"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workflow.py -v`
Expected: FAIL with import errors because `auto_weekly_ai_feedback.graph` does not exist yet.

- [ ] **Step 3: Expand tests for invalid selection and pause-after-selection behavior**

```python
def test_run_until_selection_returns_options_without_report() -> None:
    state = run_until_selection(...)
    assert "options" in state["selection"]
    assert "report_markdown" not in state


def test_run_workflow_rejects_unknown_user_selected_slug() -> None:
    with pytest.raises(ValueError, match="Invalid selected slug"):
        run_workflow(...)
```

- [ ] **Step 4: Re-run tests to verify they still fail for missing implementation**

Run: `pytest tests/test_workflow.py -v`
Expected: FAIL with the same missing-module or missing-symbol failures.

- [ ] **Step 5: Commit the red tests**

```bash
git add tests/test_workflow.py
git commit -m "test: add workflow selection tests"
```

### Task 2: Implement graph state and deterministic selection logic

**Files:**
- Create: `src/auto_weekly_ai_feedback/graph/__init__.py`
- Create: `src/auto_weekly_ai_feedback/graph/state.py`
- Create: `src/auto_weekly_ai_feedback/graph/nodes.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write the failing test for direct selection resolution**

```python
from auto_weekly_ai_feedback.graph.nodes import resolve_selection


def test_resolve_selection_prefers_recommendation_when_no_user_choice() -> None:
    state = {
        "selection": {
            "recommended_slug": "product-a",
            "options": [{"slug": "product-a", "score": 9.0, "rationale": "best", "tradeoffs": []}],
        }
    }

    result = resolve_selection(state)

    assert result["selection"]["final_slug"] == "product-a"
    assert result["selection"]["decision_mode"] == "auto"
```

- [ ] **Step 2: Run the direct selection test to verify it fails**

Run: `pytest tests/test_workflow.py::test_resolve_selection_prefers_recommendation_when_no_user_choice -v`
Expected: FAIL because `resolve_selection` does not exist yet.

- [ ] **Step 3: Implement minimal graph state and selection resolution**

```python
class SourceRef(TypedDict):
    title: str
    url: str
    source_type: str


class CandidateProduct(TypedDict):
    ...


def resolve_selection(state: GraphState) -> GraphState:
    selection = dict(state.get("selection", {}))
    options = selection.get("options", [])
    option_slugs = {option["slug"] for option in options}
    chosen_slug = selection.get("user_selected_slug") or selection.get("recommended_slug")
    if chosen_slug not in option_slugs:
        raise ValueError(f"Invalid selected slug: {chosen_slug}")
    selection["final_slug"] = chosen_slug
    selection["decision_mode"] = "user" if selection.get("user_selected_slug") else "auto"
    selection["final_rationale"] = next(option["rationale"] for option in options if option["slug"] == chosen_slug)
    return {"selection": selection}
```

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `pytest tests/test_workflow.py -k "resolve_selection or unknown_user_selected_slug" -v`
Expected: PASS for the selection-resolution tests.

- [ ] **Step 5: Commit the state and selection implementation**

```bash
git add src/auto_weekly_ai_feedback/graph/__init__.py src/auto_weekly_ai_feedback/graph/state.py src/auto_weekly_ai_feedback/graph/nodes.py tests/test_workflow.py
git commit -m "feat: add graph state and selection resolution"
```

### Task 3: Add workflow assembly and node factories

**Files:**
- Create: `src/auto_weekly_ai_feedback/graph/workflow.py`
- Modify: `src/auto_weekly_ai_feedback/agent.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write the failing tests for workflow entry points**

```python
def test_run_workflow_uses_recommended_slug_in_auto_mode() -> None:
    final_state = run_workflow(
        initial_state={"today": "2026-05-25", "days": 30, "topic": "general", "max_candidates": 4},
        search_candidates_fn=lambda state: {"candidates": [make_candidate("product-a"), make_candidate("product-b")]},
        select_product_fn=lambda state: {
            "selection": {
                "recommended_slug": "product-a",
                "options": [
                    {"slug": "product-a", "score": 9.0, "rationale": "best evidence", "tradeoffs": ["narrow audience"]},
                    {"slug": "product-b", "score": 8.0, "rationale": "good but less current", "tradeoffs": ["less documentation"]},
                ],
            }
        },
        write_editorial_review_fn=lambda state: {"report_markdown": "# Product A\n\nBody"},
    )

    assert final_state["selection"]["final_slug"] == "product-a"
    assert final_state["report_markdown"].startswith("# Product A")
```

- [ ] **Step 2: Run the workflow tests to verify they fail**

Run: `pytest tests/test_workflow.py -k "run_workflow or run_until_selection" -v`
Expected: FAIL because `run_workflow` and `run_until_selection` do not exist yet.

- [ ] **Step 3: Implement workflow builder and dependency factories**

```python
def build_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(...)


def build_tools(settings: Settings) -> list[BaseTool]:
    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
    return [TavilySearch(max_results=5, topic="general"), TavilyExtract()]


def run_until_selection(...):
    graph = build_workflow(...)
    return graph.invoke(initial_state, interrupt_before=["resolve_selection"])


def run_workflow(...):
    graph = build_workflow(...)
    return graph.invoke(initial_state)
```

- [ ] **Step 4: Run workflow tests to verify they pass**

Run: `pytest tests/test_workflow.py -k "run_workflow or run_until_selection" -v`
Expected: PASS with correct selection and report behavior.

- [ ] **Step 5: Commit workflow assembly**

```bash
git add src/auto_weekly_ai_feedback/agent.py src/auto_weekly_ai_feedback/graph/workflow.py tests/test_workflow.py
git commit -m "feat: add langgraph workflow runner"
```

### Task 4: Implement LLM-backed nodes and CLI selection modes

**Files:**
- Modify: `src/auto_weekly_ai_feedback/graph/nodes.py`
- Modify: `src/auto_weekly_ai_feedback/cli.py`
- Check: `README.md`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write the failing CLI tests for selection-mode behavior**

```python
from typer.testing import CliRunner
from auto_weekly_ai_feedback.cli import app


def test_cli_run_uses_auto_selection_mode(monkeypatch) -> None:
    ...


def test_cli_run_prompts_for_slug_in_user_mode(monkeypatch) -> None:
    ...
```

- [ ] **Step 2: Run the CLI tests to verify they fail**

Run: `pytest tests/test_workflow.py -k "cli_run" -v`
Expected: FAIL because `--selection-mode` behavior is not implemented.

- [ ] **Step 3: Implement prompts and CLI wiring**

```python
@app.command()
def run(
    ...,
    selection_mode: str = typer.Option("auto", help="Selection mode: auto or user."),
) -> None:
    if selection_mode == "user":
        state = run_until_selection(...)
        chosen_slug = Prompt.ask("Enter slug to continue", choices=[...], default=...)
        final_state = run_workflow(..., user_selected_slug=chosen_slug, ...)
    else:
        final_state = run_workflow(...)
```

Node prompt requirements:

- `search_candidates` prompt only gathers and structures candidates.
- `select_product` prompt only scores and recommends.
- `write_editorial_review` prompt only writes the editorial review for the final slug.

- [ ] **Step 4: Run CLI and workflow tests to verify they pass**

Run: `pytest tests/test_workflow.py -v`
Expected: PASS for CLI-driven selection behavior.

- [ ] **Step 5: Commit CLI and node prompt integration**

```bash
git add src/auto_weekly_ai_feedback/graph/nodes.py src/auto_weekly_ai_feedback/cli.py tests/test_workflow.py
git commit -m "feat: add selection-mode cli workflow"
```

### Task 5: Verify regression safety and finish the refactor

**Files:**
- Check: `tests/test_reporting.py`
- Check: `tests/test_filters.py`
- Check: `src/auto_weekly_ai_feedback/reporting.py`
- Check: `README.md`

- [ ] **Step 1: Run the full test suite**

Run: `pytest -v`
Expected: PASS with existing reporting/filter tests and new workflow tests all green.

- [ ] **Step 2: Run the CLI help command**

Run: `python -m auto_weekly_ai_feedback.cli run --help`
Expected: PASS and display `--selection-mode` in the options list.

- [ ] **Step 3: Update README only if the new CLI mode is not discoverable enough**

```markdown
ai-product-report run --selection-mode user
```

- [ ] **Step 4: Re-run affected tests after any doc or CLI adjustments**

Run: `pytest tests/test_workflow.py tests/test_reporting.py tests/test_filters.py -v`
Expected: PASS.

- [ ] **Step 5: Commit the verified refactor**

```bash
git add README.md tests/test_workflow.py src/auto_weekly_ai_feedback
git commit -m "feat: refactor report generation into langgraph workflow"
```
