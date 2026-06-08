from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import FORBIDDEN_REVIEW_TERMS, make_pack, read_json, run_cli
from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.artifacts import (
    CONTRACT_REVIEW_FILE_NAME,
    DATASET_PROFILES_FILE_NAME,
    INVENTORY_FILE_NAME,
    MAPPING_REVIEW_FILE_NAME,
    RECONCILIATION_RESULTS_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    TRACE_FILE_NAME,
)
from data_migration_readiness_review_agent.cli import main


def test_cli_version_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


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
    assert trace["artifacts_written"] == [
        INVENTORY_FILE_NAME,
        DATASET_PROFILES_FILE_NAME,
        SCHEMA_INVENTORY_FILE_NAME,
        MAPPING_REVIEW_FILE_NAME,
        CONTRACT_REVIEW_FILE_NAME,
        RECONCILIATION_RESULTS_FILE_NAME,
        TRACE_FILE_NAME,
    ]
    assert trace["counts"]["referenced_files_present"] == 6
    assert trace["reconciliation_summary"]["datasets_reconciled"] == 1
    assert trace["mapping_review_summary"]["mappings_reviewed"] == 1
    assert trace["contract_review_summary"]["contracts_reviewed"] == 1
    assert trace["no_llm"] is True
    assert trace["orchestrator"] == "standard"
    assert trace["status"] == "reconciliation_artifacts_created"
    assert not any(f'"status": "{term}"' in trace_text for term in FORBIDDEN_REVIEW_TERMS)
