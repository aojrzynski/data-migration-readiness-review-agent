from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from data_migration_readiness_review_agent.artifact_registry import ORDERED_ARTIFACT_FILE_NAMES
from data_migration_readiness_review_agent.cli import build_parser, build_run_config, main
from data_migration_readiness_review_agent.orchestrators import standard
from data_migration_readiness_review_agent.orchestrators.standard import run_standard_review
from data_migration_readiness_review_agent.run_config import RunConfig
from data_migration_readiness_review_agent.run_result import RunResult
from helpers import EXPECTED_ARTIFACT_FILE_ORDER, EXPECTED_ARTIFACT_FILES, make_pack, read_json

FORBIDDEN_STEP_TERMS = ("approved", "approval", "ready", "certified", "certification")


def test_run_standard_review_returns_run_result_with_expected_paths(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"
    config = RunConfig(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=None,
        no_llm=True,
        orchestrator="standard",
        llm_review=False,
        llm_provider="openai",
        llm_model=None,
        llm_max_input_chars=20000,
    )

    result = run_standard_review(config)

    assert isinstance(result, RunResult)
    assert result.status == "review_summary_artifacts_created"
    assert set(result.artifacts) == EXPECTED_ARTIFACT_FILES
    assert list(result.artifacts) == EXPECTED_ARTIFACT_FILE_ORDER
    for file_name, artifact_path in result.artifacts.items():
        assert artifact_path == output_dir / file_name
        assert artifact_path.exists()


def test_standard_orchestrator_writes_artifacts_in_deterministic_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"
    writes: list[str] = []

    def record_json(payload: dict[str, object], out_dir: Path, file_name: str) -> Path:
        writes.append(file_name)
        return out_dir / file_name

    def record_markdown(review_pack: dict[str, object], out_dir: Path, file_name: str) -> Path:
        writes.append(file_name)
        return out_dir / file_name

    monkeypatch.setattr(standard, "write_json_artifact", record_json)
    monkeypatch.setattr(standard, "write_reviewer_summary", record_markdown)

    config = RunConfig(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=None,
        no_llm=True,
        orchestrator="standard",
        llm_review=False,
        llm_provider="openai",
        llm_model=None,
        llm_max_input_chars=20000,
    )

    result = run_standard_review(config)

    assert writes == list(ORDERED_ARTIFACT_FILE_NAMES)
    assert list(result.artifacts) == list(ORDERED_ARTIFACT_FILE_NAMES)


def test_standard_orchestrator_trace_includes_artifacts_and_safe_steps(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"
    config = RunConfig(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=None,
        no_llm=True,
        orchestrator="standard",
        llm_review=False,
        llm_provider="openai",
        llm_model=None,
        llm_max_input_chars=20000,
    )

    result = run_standard_review(config)

    assert result.trace["artifacts_written"] == EXPECTED_ARTIFACT_FILE_ORDER
    assert result.trace["orchestrator"] == "standard"
    assert result.trace["orchestration"]["mode"] == "standard"
    assert "trace_created" in result.trace["orchestration"]["steps"]
    for step in result.trace["orchestration"]["steps"]:
        assert not any(term in step for term in FORBIDDEN_STEP_TERMS)


def test_standard_orchestrator_does_not_read_generated_json_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"
    original_read_text = Path.read_text

    def guard_generated_json_reads(path: Path, *args: object, **kwargs: object) -> str:
        if path.parent == output_dir and path.suffix == ".json":
            raise AssertionError(f"Generated artifact was read back from disk: {path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guard_generated_json_reads)
    config = RunConfig(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=None,
        no_llm=True,
        orchestrator="standard",
        llm_review=False,
        llm_provider="openai",
        llm_model=None,
        llm_max_input_chars=20000,
    )

    result = run_standard_review(config)

    assert result.trace["status"] == "review_summary_artifacts_created"


def test_run_config_carries_cli_inputs(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"
    manifest_path = Path("manifest.yaml")
    parser = argparse.ArgumentParser()
    args = build_parser().parse_args(
        [
            "--pack",
            str(pack_path),
            "--manifest",
            str(manifest_path),
            "--output-dir",
            str(output_dir),
            "--llm-review",
            "--llm-provider",
            "openai",
            "--llm-model",
            "unit-test-model",
            "--llm-max-input-chars",
            "321",
            "--orchestrator",
            "standard",
        ]
    )

    config = build_run_config(args, parser)

    assert config.pack_path == pack_path.resolve()
    assert config.output_dir == output_dir.resolve()
    assert config.manifest_path == manifest_path
    assert config.no_llm is False
    assert config.orchestrator == "standard"
    assert config.llm_review is True
    assert config.llm_provider == "openai"
    assert config.llm_model == "unit-test-model"
    assert config.llm_max_input_chars == 321


def test_manifest_errors_surface_as_cli_errors(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--pack",
                str(pack_path),
                "--manifest",
                "missing_manifest.yaml",
                "--output-dir",
                str(output_dir),
                "--no-llm",
            ]
        )

    assert exc_info.value.code == 2


def test_llm_conflict_validation_happens_before_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    def fail_if_called(config: RunConfig) -> RunResult:
        raise AssertionError("orchestrator should not run")

    monkeypatch.setattr(
        "data_migration_readiness_review_agent.cli.run_standard_review", fail_if_called
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--pack",
                str(pack_path),
                "--output-dir",
                str(output_dir),
                "--no-llm",
                "--llm-review",
            ]
        )

    assert exc_info.value.code == 2


def test_trace_file_matches_in_memory_trace(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"
    config = RunConfig(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=None,
        no_llm=True,
        orchestrator="standard",
        llm_review=False,
        llm_provider="openai",
        llm_model=None,
        llm_max_input_chars=20000,
    )

    result = run_standard_review(config)

    assert read_json(output_dir / "migration_readiness_trace.json") == result.trace


def test_run_config_defaults_to_standard_orchestrator(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    args = build_parser().parse_args(["--pack", str(pack_path)])

    config = build_run_config(args, argparse.ArgumentParser())

    assert config.orchestrator == "standard"


def test_langgraph_orchestrator_without_optional_dependency_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    def dependency_missing(config: RunConfig) -> RunResult:
        from data_migration_readiness_review_agent.orchestrators.langgraph import (
            LANGGRAPH_DEPENDENCY_ERROR,
            LangGraphDependencyError,
        )

        raise LangGraphDependencyError(LANGGRAPH_DEPENDENCY_ERROR)

    monkeypatch.setattr(
        "data_migration_readiness_review_agent.cli.run_langgraph_review", dependency_missing
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--pack",
                str(pack_path),
                "--output-dir",
                str(output_dir),
                "--no-llm",
                "--orchestrator",
                "langgraph",
            ]
        )

    assert exc_info.value.code == 2
    assert "optional graph dependency" in capsys.readouterr().err
    assert not output_dir.exists()


def test_llm_conflict_validation_happens_before_langgraph_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    def fail_if_called(config: RunConfig) -> RunResult:
        raise AssertionError("orchestrator should not run")

    monkeypatch.setattr(
        "data_migration_readiness_review_agent.cli.run_langgraph_review", fail_if_called
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--pack",
                str(pack_path),
                "--output-dir",
                str(output_dir),
                "--no-llm",
                "--llm-review",
                "--orchestrator",
                "langgraph",
            ]
        )

    assert exc_info.value.code == 2


def test_llm_max_input_validation_happens_before_langgraph_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    def fail_if_called(config: RunConfig) -> RunResult:
        raise AssertionError("orchestrator should not run")

    monkeypatch.setattr(
        "data_migration_readiness_review_agent.cli.run_langgraph_review", fail_if_called
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--pack",
                str(pack_path),
                "--output-dir",
                str(output_dir),
                "--llm-max-input-chars",
                "0",
                "--orchestrator",
                "langgraph",
            ]
        )

    assert exc_info.value.code == 2
