from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from data_migration_readiness_review_agent.artifact_registry import (
    LLM_REVIEWER_NOTES_FILE_NAME,
    ORDERED_ARTIFACT_FILE_NAMES,
    REVIEW_PACK_FILE_NAME,
    TRACE_FILE_NAME,
)
from data_migration_readiness_review_agent.orchestrators.langgraph import run_langgraph_review
from data_migration_readiness_review_agent.orchestrators.standard import run_standard_review
from data_migration_readiness_review_agent.run_config import RunConfig
from data_migration_readiness_review_agent.run_result import RunResult
from helpers import EXPECTED_ARTIFACT_FILE_ORDER, EXPECTED_ARTIFACT_FILES, make_pack, read_json

FORBIDDEN_STEP_TERMS = ("approved", "approval", "ready", "certified", "certification", "go_live")


class FakeCompiledGraph:
    def __init__(self, nodes: dict[str, Any], edges: dict[str, str]) -> None:
        self.nodes = nodes
        self.edges = edges

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        current = self.edges["__start__"]
        while current != "__end__":
            state = self.nodes[current](state)
            current = self.edges[current]
        return state


class FakeStateGraph:
    def __init__(self, state_schema: object) -> None:
        self.state_schema = state_schema
        self.nodes: dict[str, Any] = {}
        self.edges: dict[str, str] = {}

    def add_node(self, name: str, node: Any) -> None:
        self.nodes[name] = node

    def add_edge(self, start: str, end: str) -> None:
        self.edges[start] = end

    def compile(self) -> FakeCompiledGraph:
        return FakeCompiledGraph(self.nodes, self.edges)


@pytest.fixture()
def fake_langgraph(monkeypatch: pytest.MonkeyPatch) -> None:
    package = types.ModuleType("langgraph")
    graph = types.ModuleType("langgraph.graph")
    graph.StateGraph = FakeStateGraph
    graph.START = "__start__"
    graph.END = "__end__"
    monkeypatch.setitem(sys.modules, "langgraph", package)
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph)


def make_config(pack_path: Path, output_dir: Path, orchestrator: str) -> RunConfig:
    return RunConfig(
        pack_path=pack_path,
        output_dir=output_dir,
        manifest_path=None,
        no_llm=True,
        orchestrator=orchestrator,
        llm_review=False,
        llm_provider="openai",
        llm_model=None,
        llm_max_input_chars=20000,
    )


def test_fake_langgraph_orchestrator_returns_result_and_writes_expected_artifacts(
    tmp_path: Path, fake_langgraph: None
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    result = run_langgraph_review(make_config(pack_path, output_dir, "langgraph"))

    assert isinstance(result, RunResult)
    assert result.status == "review_summary_artifacts_created"
    assert set(result.artifacts) == EXPECTED_ARTIFACT_FILES
    assert list(result.artifacts) == EXPECTED_ARTIFACT_FILE_ORDER
    for file_name in ORDERED_ARTIFACT_FILE_NAMES:
        assert (output_dir / file_name).exists()


def test_fake_langgraph_trace_records_mode_implementation_and_safe_steps(
    tmp_path: Path, fake_langgraph: None
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    result = run_langgraph_review(make_config(pack_path, output_dir, "langgraph"))

    assert result.trace["orchestrator"] == "langgraph"
    assert result.trace["orchestration"]["mode"] == "langgraph"
    assert result.trace["orchestration"]["implementation"] == "langgraph"
    assert result.trace["orchestration"]["steps"][-1] == "artifacts_written"
    for step in result.trace["orchestration"]["steps"]:
        assert not any(term in step for term in FORBIDDEN_STEP_TERMS)


def test_fake_langgraph_orchestrator_does_not_read_generated_json_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_langgraph: None
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"
    original_read_text = Path.read_text

    def guard_generated_json_reads(path: Path, *args: object, **kwargs: object) -> str:
        if path.parent == output_dir and path.suffix == ".json":
            raise AssertionError(f"Generated artifact was read back from disk: {path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guard_generated_json_reads)

    result = run_langgraph_review(make_config(pack_path, output_dir, "langgraph"))

    assert result.trace["status"] == "review_summary_artifacts_created"


def test_fake_langgraph_no_llm_writes_not_requested_notes(
    tmp_path: Path, fake_langgraph: None
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_langgraph_review(make_config(pack_path, output_dir, "langgraph"))

    notes = read_json(output_dir / LLM_REVIEWER_NOTES_FILE_NAME)
    assert notes["status"] == "llm_review_not_requested"
    assert notes["llm_requested"] is False


def test_standard_and_fake_langgraph_have_equivalent_artifact_set_and_core_summaries(
    tmp_path: Path, fake_langgraph: None
) -> None:
    pack_path = make_pack(tmp_path)
    standard_output = tmp_path / "standard"
    langgraph_output = tmp_path / "langgraph"

    standard_result = run_standard_review(make_config(pack_path, standard_output, "standard"))
    langgraph_result = run_langgraph_review(make_config(pack_path, langgraph_output, "langgraph"))

    assert list(standard_result.artifacts) == list(langgraph_result.artifacts)
    standard_review_pack = read_json(standard_output / REVIEW_PACK_FILE_NAME)
    langgraph_review_pack = read_json(langgraph_output / REVIEW_PACK_FILE_NAME)
    assert standard_review_pack["summary"] == langgraph_review_pack["summary"]
    assert (
        standard_result.trace["llm_review_summary"]
        == langgraph_result.trace["llm_review_summary"]
    )


def test_langgraph_trace_step_names_do_not_use_forbidden_verdict_terms(
    tmp_path: Path, fake_langgraph: None
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_langgraph_review(make_config(pack_path, output_dir, "langgraph"))

    trace_text = json.dumps(read_json(output_dir / TRACE_FILE_NAME)).lower()
    assert not any(term in trace_text for term in ("approved", "certified", "go_live"))
