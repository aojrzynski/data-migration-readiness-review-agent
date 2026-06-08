from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli import TRACE_FILE_NAME, main

FORBIDDEN_TRACE_TERMS = {
    "ready",
    "approved",
    "compliant",
    "certified",
    "go_live_approved",
}


def test_cli_version_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_valid_pack_writes_trace(tmp_path: Path) -> None:
    pack_path = tmp_path / "pack"
    output_dir = tmp_path / "outputs"
    pack_path.mkdir()

    exit_code = main(
        [
            "--pack",
            str(pack_path),
            "--output-dir",
            str(output_dir),
            "--no-llm",
            "--orchestrator",
            "standard",
        ]
    )

    trace_path = output_dir / TRACE_FILE_NAME
    assert exit_code == 0
    assert trace_path.exists()


def test_cli_missing_pack_path_raises_system_exit(tmp_path: Path) -> None:
    missing_pack_path = tmp_path / "missing-pack"

    with pytest.raises(SystemExit) as exc_info:
        main(["--pack", str(missing_pack_path), "--output-dir", str(tmp_path / "outputs")])

    assert exc_info.value.code != 0


def test_trace_contains_no_llm_and_orchestrator_values(tmp_path: Path) -> None:
    pack_path = tmp_path / "pack"
    output_dir = tmp_path / "outputs"
    pack_path.mkdir()

    main(
        [
            "--pack",
            str(pack_path),
            "--output-dir",
            str(output_dir),
            "--no-llm",
            "--orchestrator",
            "standard",
        ]
    )

    trace = json.loads((output_dir / TRACE_FILE_NAME).read_text(encoding="utf-8"))
    assert trace["no_llm"] is True
    assert trace["orchestrator"] == "standard"


def test_trace_uses_safe_scaffold_wording(tmp_path: Path) -> None:
    pack_path = tmp_path / "pack"
    output_dir = tmp_path / "outputs"
    pack_path.mkdir()

    main(["--pack", str(pack_path), "--output-dir", str(output_dir)])

    trace_text = (output_dir / TRACE_FILE_NAME).read_text(encoding="utf-8").lower()
    trace = json.loads(trace_text)
    assert trace["status"] == "scaffold_trace_written"
    assert not any(f'"status": "{term}"' in trace_text for term in FORBIDDEN_TRACE_TERMS)
