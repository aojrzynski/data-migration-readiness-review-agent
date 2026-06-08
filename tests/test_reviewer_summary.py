from __future__ import annotations

from pathlib import Path

import pytest

from conftest import make_pack, read_json, run_cli
from data_migration_readiness_review_agent.artifacts import (
    REVIEW_PACK_FILE_NAME,
    REVIEWER_SUMMARY_FILE_NAME,
)
from data_migration_readiness_review_agent.reviewer_summary import build_reviewer_summary_markdown
from data_migration_readiness_review_agent.safe_language import (
    assert_safe_generated_text,
    find_forbidden_terms,
)


def run_and_read_summary(tmp_path: Path, pack_path: Path) -> tuple[str, dict[str, object]]:
    output_dir = tmp_path / "outputs"
    assert run_cli(pack_path, output_dir) == 0
    return (
        (output_dir / REVIEWER_SUMMARY_FILE_NAME).read_text(encoding="utf-8"),
        read_json(output_dir / REVIEW_PACK_FILE_NAME),
    )


def test_reviewer_summary_is_written_with_scope_artifact_index_and_boundary(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    summary, _ = run_and_read_summary(tmp_path, pack_path)

    assert "# Data Migration Review Summary" in summary
    assert "Migration: customer_account_migration" in summary
    assert "## Artifact index" in summary
    assert "migration_inventory.json" in summary
    assert "does not assess readiness" in summary
    assert "approve migration" in summary
    assert "decide go-live" in summary
    assert "certify compliance" in summary
    assert "replace human review" in summary


def test_reviewer_summary_includes_counts_grouped_findings_and_checklist(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    summary, _ = run_and_read_summary(tmp_path, pack_path)

    assert "## Summary counts" in summary
    assert "| Datasets | 1 |" in summary
    assert "## Findings for human review" in summary
    assert "### Sensitive-field indicators" in summary
    assert "- [ ] Confirm handling expectations for sensitive-field indicators" in summary


def test_reviewer_summary_omits_raw_csv_values(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    summary, _ = run_and_read_summary(tmp_path, pack_path)

    assert "example@example.com" not in summary
    assert "second@example.com" not in summary
    assert "555-0100" not in summary
    assert "555-0101" not in summary


def test_reviewer_summary_allows_only_negated_forbidden_language(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    summary, _ = run_and_read_summary(tmp_path, pack_path)

    assert find_forbidden_terms(summary) == []


def test_reviewer_summary_states_when_category_has_no_findings(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    summary, _ = run_and_read_summary(tmp_path, pack_path)

    assert "### Migration pack inventory\n\nNo findings generated for this category." in summary


def test_safe_language_helper_catches_positive_verdict_phrases() -> None:
    with pytest.raises(ValueError):
        assert_safe_generated_text(
            "The migration is ready and has a readiness score.", context="unit test"
        )


def test_build_reviewer_summary_markdown_returns_safe_text(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    _, review_pack = run_and_read_summary(tmp_path, pack_path)

    summary = build_reviewer_summary_markdown(review_pack)

    assert summary.startswith("# Data Migration Review Summary")
    assert find_forbidden_terms(summary) == []
