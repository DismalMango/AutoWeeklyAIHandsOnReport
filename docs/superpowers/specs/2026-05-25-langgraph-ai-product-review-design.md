# LangGraph AI Product Review Design

## Goal

Refactor the current single-shot `AIProductAgent` flow into a LangGraph workflow that constrains LLM behavior through explicit node boundaries. The first iteration focuses on four responsibilities:

1. Search for recent AI product candidates.
2. Score and recommend several candidates.
3. Resolve the final product selection through either automatic or user-driven choice.
4. Generate an editorial-style Chinese review centered on product experience and judgment.

This design intentionally separates fact gathering, product selection, and editorial writing so each LLM call has one narrow job.

## Current Baseline

The current implementation in `src/auto_weekly_ai_feedback/agent.py` performs the full workflow in one agent invocation:

- search for recent products
- choose one product
- collect supporting public information
- write the final Markdown report

That implementation works for a single report, but it does not expose explicit workflow state, decision traces, or user intervention points. It is difficult to constrain or inspect whether the model is currently searching, selecting, or writing.

## Scope

This design covers the first LangGraph-based workflow only. It does not include:

- account registration or hands-on product operation
- browser automation
- persistence of intermediate state to a database
- advanced retry, branching, or human-review queues

The design keeps these future extensions possible without overbuilding the first version.

## Workflow

The workflow graph is:

`search_candidates -> select_product -> resolve_selection -> write_editorial_review`

### `search_candidates`

Input:

- `today`
- `days`
- `topic`
- `max_candidates`

Output:

- `candidates`

Responsibilities:

- search for recent AI-native product candidates within the requested time window
- gather multiple public sources per candidate
- normalize results into a structured candidate list

Non-responsibilities:

- final recommendation
- final report writing

### `select_product`

Input:

- `candidates`

Output:

- `selection.options`
- `selection.recommended_slug`

Responsibilities:

- score the candidate pool using explicit product-selection criteria
- produce a short list of 2-4 viable options
- recommend one option and explain tradeoffs

Non-responsibilities:

- forcing the final product choice
- writing the report

### `resolve_selection`

Input:

- `selection.options`
- optional `selection.user_selected_slug`

Output:

- `selection.final_slug`
- `selection.decision_mode`
- `selection.final_rationale`

Responsibilities:

- convert recommendation into a final selection
- support both fully automatic and user-interactive CLI flows

Behavior:

- if no user choice is provided, use `recommended_slug`
- if a user choice is provided, validate it against available options and use it as the final selection

This node is deterministic Python logic, not an LLM call.

### `write_editorial_review`

Input:

- `candidates`
- `selection.final_slug`
- run parameters such as `today`

Output:

- `report_markdown`

Responsibilities:

- write a Chinese editorial-style review for the final product
- emphasize positioning, experience framing, strengths, limitations, and suitability
- ground every claim in public sources already gathered upstream

Non-responsibilities:

- changing the selected product
- performing broad new candidate discovery

## State Model

The workflow state is intentionally structured and minimal. Nodes pass normalized facts rather than raw Tavily responses.

```python
class SourceRef(TypedDict):
    title: str
    url: str
    source_type: str  # official, launch, docs, review, discussion


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
    decision_mode: str  # auto | user
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
```

## Selection Criteria

`select_product` should use one stable set of selection criteria so its recommendation remains interpretable.

Recommended criteria for the first version:

- recency of launch, update, or discussion signals
- strength of AI-native positioning
- clarity of target user and usage scenario
- completeness and diversity of public evidence
- likely value of the product as a report subject

The node should not hide the rationale in freeform prose only. It should preserve candidate-level tradeoffs in `selection.options`.

## Editorial Review Shape

The final report should be an editorial-style review, not a raw research dump and not a first-person hands-on claim.

Expected qualities:

- strong one-line positioning
- experience framing based on public flows and materials
- clear explanation of what feels compelling versus what may feel costly or constrained
- explicit suitable and unsuitable audiences
- visible evidence links

The report must continue to state that it is based on public information rather than real account-level product usage.

## File Structure Changes

Recommended structure:

- `src/auto_weekly_ai_feedback/graph/state.py`
- `src/auto_weekly_ai_feedback/graph/nodes.py`
- `src/auto_weekly_ai_feedback/graph/workflow.py`
- `src/auto_weekly_ai_feedback/agent.py`
- `src/auto_weekly_ai_feedback/cli.py`

### `graph/state.py`

Define typed state objects and helper types.

### `graph/nodes.py`

Implement the four node functions:

- `search_candidates`
- `select_product`
- `resolve_selection`
- `write_editorial_review`

### `graph/workflow.py`

Build the LangGraph workflow and expose a run entry point that accepts CLI parameters and returns the final state.

### `agent.py`

Shrink this file into factories for shared runtime dependencies:

- build chat model
- build Tavily tools

It should stop owning the entire end-to-end report flow.

### `cli.py`

Replace the direct `AIProductAgent.run()` call with graph execution.

Add a new option:

- `--selection-mode auto`
- `--selection-mode user`

For `user` mode:

- run the graph through `select_product`
- display the candidate options and recommended choice
- ask the user to choose a candidate slug
- resume the workflow with `user_selected_slug`

## Implementation Strategy

Recommended implementation strategy:

1. Use LangGraph with pure node functions.
2. Make `search_candidates`, `select_product`, and `write_editorial_review` separate LLM calls.
3. Keep `resolve_selection` as deterministic Python logic.
4. Reuse existing OpenAI model and Tavily tool setup from the current code.

This is preferred over embedding full LangChain agents inside every node, because the goal is to constrain behavior through explicit node boundaries rather than preserve black-box autonomy inside each stage.

## Error Handling

First-version error handling should stay simple and explicit.

- if no candidates are returned, fail with a clear workflow error
- if the user selects an invalid slug, fail with a clear validation error
- if the final product cannot be matched back to a candidate, fail before report generation
- preserve human-readable errors in `errors` when useful

Retries, fallbacks, and branch recovery can be added later without changing the state model.

## Testing Strategy

The first version should add targeted tests around deterministic behavior and state transitions.

Priority test areas:

- `resolve_selection` auto mode uses `recommended_slug`
- `resolve_selection` user mode accepts valid slugs
- invalid user selection raises a clear error
- graph assembly connects nodes in the expected order
- report writing consumes `final_slug` rather than reselecting

LLM output quality itself does not need strict snapshot testing in the first pass. Tests should focus on workflow invariants and Python-controlled behavior.

## Migration Notes

This is a refactor of orchestration, not a product rewrite.

- existing report-writing output path can remain unchanged
- existing settings loading can remain unchanged
- existing model and Tavily configuration can remain unchanged
- the single-shot prompt should be decomposed into node-specific prompts

The prompt split is important: each node prompt must describe only its own responsibility. The workflow should not preserve the current “one prompt does everything” design inside a new graph shell.

## Recommended Next Step

After this design is approved, the next artifact should be a concrete implementation plan that sequences:

1. state and type definitions
2. workflow builder
3. node prompt decomposition
4. CLI selection-mode integration
5. tests for deterministic selection behavior
