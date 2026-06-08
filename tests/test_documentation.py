from __future__ import annotations

from pathlib import Path

from data_migration_readiness_review_agent.safe_language import find_forbidden_terms

DOC_FILES = [
    Path("docs/architecture.md"),
    Path("docs/design_principles.md"),
    Path("docs/artifacts.md"),
    Path("docs/demo_workflow.md"),
    Path("docs/example_commands.md"),
    Path("docs/migration_pack_format.md"),
    Path("docs/reviewer_workflow.md"),
    Path("docs/safety_boundaries.md"),
    Path("docs/llm_reviewer_notes.md"),
    Path("docs/orchestration.md"),
    Path("docs/roadmap.md"),
]

ARTIFACTS = [
    "migration_inventory.json",
    "dataset_profiles.json",
    "schema_inventory.json",
    "mapping_review.json",
    "contract_review.json",
    "reconciliation_results.json",
    "sensitive_field_review.json",
    "test_evidence_review.json",
    "evidence_coverage_review.json",
    "review_pack.json",
    "reviewer_summary.md",
    "llm_reviewer_notes.json",
    "migration_readiness_trace.json",
]

LLM_STATUSES = [
    "llm_review_not_requested",
    "llm_review_skipped",
    "llm_review_completed",
    "llm_review_failed",
    "llm_review_rejected",
]


def test_documentation_files_exist() -> None:
    for path in DOC_FILES:
        assert path.exists(), path


def test_readme_links_to_all_final_docs_files() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    for path in DOC_FILES:
        assert f"]({path.as_posix()})" in readme


def test_readme_names_reviewer_summary_as_first_file_to_open() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Open `reviewer_summary.md` first" in readme
    assert "The workplace problem" in readme
    assert "source extracts" in readme
    assert "target extracts" in readme
    assert "what needs follow-up" in readme


def test_artifacts_doc_documents_all_current_artifacts() -> None:
    artifacts_doc = Path("docs/artifacts.md").read_text(encoding="utf-8")

    for artifact in ARTIFACTS:
        assert f"## `{artifact}`" in artifacts_doc
        assert "### Purpose" in artifacts_doc
        assert "### When written" in artifacts_doc
        assert "### Open it for" in artifacts_doc
        assert "### What it contains" in artifacts_doc
        assert "### What it excludes" in artifacts_doc
        assert "### Artifact type" in artifacts_doc
        assert "### Authority boundary" in artifacts_doc


def test_example_commands_cover_standard_llm_and_langgraph() -> None:
    commands_doc = Path("docs/example_commands.md").read_text(encoding="utf-8")

    assert "--no-llm" in commands_doc
    assert "--llm-review" in commands_doc
    assert "--orchestrator langgraph" in commands_doc
    assert '.[dev,llm]' in commands_doc
    assert '.[dev,graph]' in commands_doc


def test_safety_boundaries_mentions_raw_rows_and_llm_input_boundaries() -> None:
    safety_doc = Path("docs/safety_boundaries.md").read_text(encoding="utf-8")

    assert "Raw data and preview policy" in safety_doc
    assert "Raw rows should not be copied" in safety_doc
    assert "Optional LLM input boundary" in safety_doc
    assert "LLM context should not include raw rows or raw sensitive values" in safety_doc


def test_orchestration_mentions_standard_and_langgraph() -> None:
    orchestration_doc = Path("docs/orchestration.md").read_text(encoding="utf-8")

    assert "standard" in orchestration_doc
    assert "langgraph" in orchestration_doc
    assert "LangGraph" in orchestration_doc


def test_llm_reviewer_notes_documents_statuses() -> None:
    llm_doc = Path("docs/llm_reviewer_notes.md").read_text(encoding="utf-8")

    for status in LLM_STATUSES:
        assert status in llm_doc


def test_roadmap_exists() -> None:
    assert Path("docs/roadmap.md").exists()


def test_docs_do_not_use_unsafe_positive_verdict_language() -> None:
    for path in [Path("README.md"), *DOC_FILES]:
        text = path.read_text(encoding="utf-8")
        assert find_forbidden_terms(text) == [], path
