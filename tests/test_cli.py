from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.artifacts import (
    CONTRACT_REVIEW_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
    INVENTORY_FILE_NAME,
    LLM_REVIEWER_NOTES_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    RECONCILIATION_RESULTS_FILE_NAME,
    REVIEW_PACK_FILE_NAME,
    REVIEWER_SUMMARY_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    SENSITIVE_FIELD_REVIEW_FILE_NAME,
    TEST_EVIDENCE_REVIEW_FILE_NAME,
    TRACE_FILE_NAME,
)
from data_migration_readiness_review_agent.cli import main
from helpers import (
    EXPECTED_ARTIFACT_FILE_ORDER,
    FORBIDDEN_REVIEW_TERMS,
    make_pack,
    read_json,
    run_cli,
)


def test_cli_version_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_orchestrator_help_text_is_pr_agnostic(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    help_text = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "PR #6" not in help_text
    assert "PR #9 supports openai only" not in help_text
    assert "optional LLM reviewer currently supports openai only." in help_text
    assert "standard" in help_text
    assert "langgraph" in help_text
    assert "graph extra" in help_text


def test_valid_pack_writes_expected_artifacts(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    assert exit_code == 0
    for file_name in [
        INVENTORY_FILE_NAME,
        DATASET_PROFILES_FILE_NAME,
        SCHEMA_INVENTORY_FILE_NAME,
        MAPPING_REVIEW_FILE_NAME,
        CONTRACT_REVIEW_FILE_NAME,
        RECONCILIATION_RESULTS_FILE_NAME,
        SENSITIVE_FIELD_REVIEW_FILE_NAME,
        TEST_EVIDENCE_REVIEW_FILE_NAME,
        EVIDENCE_COVERAGE_REVIEW_FILE_NAME,
        REVIEW_PACK_FILE_NAME,
        REVIEWER_SUMMARY_FILE_NAME,
        LLM_REVIEWER_NOTES_FILE_NAME,
        TRACE_FILE_NAME,
    ]:
        assert (output_dir / file_name).exists()


def test_trace_includes_artifacts_summaries_and_safe_status(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    trace = read_json(output_dir / TRACE_FILE_NAME)
    trace_text = json.dumps(trace).lower()
    assert trace["manifest_path"].endswith("manifest.yaml")
    assert trace["artifacts_written"] == EXPECTED_ARTIFACT_FILE_ORDER
    assert trace["counts"]["referenced_files_present"] == 6
    assert trace["reconciliation_summary"]["datasets_reconciled"] == 1
    assert trace["sensitive_field_summary"]["datasets_reviewed"] == 1
    assert trace["test_evidence_summary"]["test_results_expected"] == 1
    assert trace["evidence_coverage_summary"]["expected_evidence_types"] == 5
    assert trace["mapping_review_summary"]["mappings_reviewed"] == 1
    assert trace["contract_review_summary"]["contracts_reviewed"] == 1
    assert trace["no_llm"] is True
    assert trace["orchestrator"] == "standard"
    assert trace["orchestration"]["mode"] == "standard"
    assert trace["review_pack_summary"]["datasets"] == 1
    assert trace["reviewer_summary_written"] is True
    assert trace["llm_review_summary"] == {
        "llm_requested": False,
        "llm_performed": False,
        "llm_status": "llm_review_not_requested",
        "provider": None,
        "model": None,
        "input_truncated": False,
    }
    assert trace["status"] == "review_summary_artifacts_created"
    assert not any(f'"status": "{term}"' in trace_text for term in FORBIDDEN_REVIEW_TERMS)


def test_forbidden_runtime_dependencies_are_not_added() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8").casefold()

    dependencies_block = pyproject.split("[project.optional-dependencies]", 1)[0]
    assert "openai" not in dependencies_block
    assert "llm = [" in pyproject
    assert "openai>=1.0.0" in pyproject
    assert "graph = [" in pyproject
    assert "langgraph" in pyproject
    for package_name in ("pandas", "openpyxl"):
        assert package_name not in pyproject


def test_llm_review_and_no_llm_conflict_exits_nonzero(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    with pytest.raises(SystemExit) as exc_info:
        main(
            ["--pack", str(pack_path), "--output-dir", str(output_dir), "--no-llm", "--llm-review"]
        )

    assert exc_info.value.code == 2


def test_llm_max_input_chars_below_one_exits_nonzero(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--pack",
                str(pack_path),
                "--output-dir",
                str(output_dir),
                "--llm-max-input-chars",
                "0",
            ]
        )

    assert exc_info.value.code == 2


def test_llm_review_without_model_is_skipped_without_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    assert main(["--pack", str(pack_path), "--output-dir", str(output_dir), "--llm-review"]) == 0

    notes = read_json(output_dir / LLM_REVIEWER_NOTES_FILE_NAME)
    assert notes["status"] == "llm_review_skipped"
    assert notes["model"] is None
    assert "no model was supplied" in notes["warnings"][0]


def test_llm_model_and_max_input_chars_are_recorded_when_dependency_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    assert (
        main(
            [
                "--pack",
                str(pack_path),
                "--output-dir",
                str(output_dir),
                "--llm-review",
                "--llm-model",
                "unit-test-model",
                "--llm-max-input-chars",
                "123",
            ]
        )
        == 0
    )

    notes = read_json(output_dir / LLM_REVIEWER_NOTES_FILE_NAME)
    assert notes["model"] == "unit-test-model"
    assert notes["input_policy"]["max_input_chars"] == 123


def test_openai_model_env_is_used_when_cli_model_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "env-test-model")
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    assert main(["--pack", str(pack_path), "--output-dir", str(output_dir), "--llm-review"]) == 0

    notes = read_json(output_dir / LLM_REVIEWER_NOTES_FILE_NAME)
    assert notes["model"] == "env-test-model"
