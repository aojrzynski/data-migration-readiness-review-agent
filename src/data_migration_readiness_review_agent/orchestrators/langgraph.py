from __future__ import annotations

from typing import Any

from data_migration_readiness_review_agent.artifact_registry import REVIEWER_SUMMARY_FILE_NAME
from data_migration_readiness_review_agent.contract_review import build_contract_review
from data_migration_readiness_review_agent.csv_profile import build_dataset_profiles
from data_migration_readiness_review_agent.evidence_coverage import build_evidence_coverage_review
from data_migration_readiness_review_agent.inventory import build_inventory
from data_migration_readiness_review_agent.llm_review import build_llm_reviewer_notes
from data_migration_readiness_review_agent.manifest import load_manifest
from data_migration_readiness_review_agent.mapping_review import build_mapping_review
from data_migration_readiness_review_agent.orchestrators.standard import (
    ReviewArtifacts,
    build_dataset_profile_summary,
    build_llm_review_summary,
    build_trace,
    write_review_artifacts,
)
from data_migration_readiness_review_agent.reconciliation import build_reconciliation_results
from data_migration_readiness_review_agent.review_pack import build_review_pack
from data_migration_readiness_review_agent.run_config import RunConfig
from data_migration_readiness_review_agent.run_result import RunResult
from data_migration_readiness_review_agent.schema_inventory import (
    build_schema_inventory,
    build_schema_summary,
)
from data_migration_readiness_review_agent.sensitive_fields import build_sensitive_field_review
from data_migration_readiness_review_agent.test_evidence import build_test_evidence_review

LANGGRAPH_DEPENDENCY_ERROR = (
    "The langgraph orchestrator requires the optional graph dependency. "
    'Install with python -m pip install -e ".[dev,graph]".'
)

LANGGRAPH_ORCHESTRATION_STEPS = [
    "manifest_loaded",
    "inventory_created",
    "dataset_profiles_created",
    "schema_inventory_created",
    "mapping_review_created",
    "contract_review_created",
    "reconciliation_created",
    "sensitive_field_review_created",
    "test_evidence_review_created",
    "evidence_coverage_review_created",
    "review_pack_created",
    "reviewer_summary_created",
    "llm_reviewer_notes_created",
    "trace_created",
    "artifacts_written",
]


class LangGraphDependencyError(RuntimeError):
    """Raised when the optional LangGraph dependency is requested but unavailable."""


def _load_langgraph_components() -> tuple[Any, Any, Any]:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise LangGraphDependencyError(LANGGRAPH_DEPENDENCY_ERROR) from exc
    return StateGraph, START, END


def _add_sequential_node(graph: Any, previous: str, node_name: str, node: Any) -> str:
    graph.add_node(node_name, node)
    graph.add_edge(previous, node_name)
    return node_name


def _build_graph(StateGraph: Any, START: Any, END: Any) -> Any:
    graph = StateGraph(dict)
    previous = START
    for node_name, node in [
        ("load_manifest", _load_manifest),
        ("build_inventory", _build_inventory),
        ("build_dataset_profiles", _build_dataset_profiles),
        ("build_schema_inventory", _build_schema_inventory),
        ("build_mapping_review", _build_mapping_review),
        ("build_contract_review", _build_contract_review),
        ("build_reconciliation_results", _build_reconciliation_results),
        ("build_sensitive_field_review", _build_sensitive_field_review),
        ("build_test_evidence_review", _build_test_evidence_review),
        ("build_evidence_coverage_review", _build_evidence_coverage_review),
        ("build_review_pack", _build_review_pack),
        ("build_llm_reviewer_notes", _build_llm_reviewer_notes),
        ("build_trace", _build_trace),
        ("write_artifacts", _write_artifacts),
    ]:
        previous = _add_sequential_node(graph, previous, node_name, node)
    graph.add_edge(previous, END)
    return graph.compile()


def _load_manifest(state: dict[str, Any]) -> dict[str, Any]:
    config: RunConfig = state["config"]
    state["loaded_manifest"] = load_manifest(config.pack_path, config.manifest_path)
    return state


def _build_inventory(state: dict[str, Any]) -> dict[str, Any]:
    state["inventory"] = build_inventory(state["loaded_manifest"])
    return state


def _build_dataset_profiles(state: dict[str, Any]) -> dict[str, Any]:
    state["dataset_profiles"] = build_dataset_profiles(state["loaded_manifest"])
    return state


def _build_schema_inventory(state: dict[str, Any]) -> dict[str, Any]:
    state["schema_inventory"] = build_schema_inventory(state["dataset_profiles"])
    return state


def _build_mapping_review(state: dict[str, Any]) -> dict[str, Any]:
    state["mapping_review"] = build_mapping_review(
        state["loaded_manifest"], state["schema_inventory"]
    )
    return state


def _build_contract_review(state: dict[str, Any]) -> dict[str, Any]:
    state["contract_review"] = build_contract_review(
        state["loaded_manifest"], state["dataset_profiles"], state["schema_inventory"]
    )
    return state


def _build_reconciliation_results(state: dict[str, Any]) -> dict[str, Any]:
    state["reconciliation_results"] = build_reconciliation_results(
        state["loaded_manifest"],
        state["dataset_profiles"],
        state["schema_inventory"],
        state["mapping_review"],
    )
    return state


def _build_sensitive_field_review(state: dict[str, Any]) -> dict[str, Any]:
    state["sensitive_field_review"] = build_sensitive_field_review(
        state["loaded_manifest"],
        state["schema_inventory"],
        state["dataset_profiles"],
        state["mapping_review"],
        state["contract_review"],
    )
    return state


def _build_test_evidence_review(state: dict[str, Any]) -> dict[str, Any]:
    state["test_evidence_review"] = build_test_evidence_review(state["loaded_manifest"])
    return state


def _build_evidence_coverage_review(state: dict[str, Any]) -> dict[str, Any]:
    state["evidence_coverage_review"] = build_evidence_coverage_review(state["loaded_manifest"])
    return state


def _build_review_pack(state: dict[str, Any]) -> dict[str, Any]:
    state["review_pack"] = build_review_pack(
        inventory=state["inventory"],
        dataset_profiles=state["dataset_profiles"],
        mapping_review=state["mapping_review"],
        contract_review=state["contract_review"],
        reconciliation_results=state["reconciliation_results"],
        sensitive_field_review=state["sensitive_field_review"],
        test_evidence_review=state["test_evidence_review"],
        evidence_coverage_review=state["evidence_coverage_review"],
    )
    state["reviewer_summary_path"] = state["config"].output_dir / REVIEWER_SUMMARY_FILE_NAME
    return state


def _build_llm_reviewer_notes(state: dict[str, Any]) -> dict[str, Any]:
    config: RunConfig = state["config"]
    state["llm_reviewer_notes"] = build_llm_reviewer_notes(
        review_pack=state["review_pack"],
        llm_requested=config.llm_review,
        provider=config.llm_provider,
        model=config.llm_model,
        max_input_chars=config.llm_max_input_chars,
    )
    return state


def _build_trace(state: dict[str, Any]) -> dict[str, Any]:
    config: RunConfig = state["config"]
    state["trace"] = build_trace(
        config=config,
        resolved_manifest_path=state["loaded_manifest"].manifest_path,
        inventory_counts=state["inventory"]["counts"],
        dataset_profile_summary=build_dataset_profile_summary(state["dataset_profiles"]),
        schema_inventory_summary=build_schema_summary(state["schema_inventory"]),
        mapping_review_summary=state["mapping_review"]["summary"],
        contract_review_summary=state["contract_review"]["summary"],
        reconciliation_summary=state["reconciliation_results"]["summary"],
        sensitive_field_summary=state["sensitive_field_review"]["summary"],
        test_evidence_summary=state["test_evidence_review"]["summary"],
        evidence_coverage_summary=state["evidence_coverage_review"]["summary"],
        review_pack_summary=state["review_pack"]["summary"],
        reviewer_summary_path=state["reviewer_summary_path"],
        llm_review_summary=build_llm_review_summary(state["llm_reviewer_notes"]),
        orchestration_mode="langgraph",
        orchestration_steps=LANGGRAPH_ORCHESTRATION_STEPS,
        orchestration_implementation="langgraph",
    )
    return state


def _write_artifacts(state: dict[str, Any]) -> dict[str, Any]:
    artifacts = ReviewArtifacts(
        inventory=state["inventory"],
        dataset_profiles=state["dataset_profiles"],
        schema_inventory=state["schema_inventory"],
        mapping_review=state["mapping_review"],
        contract_review=state["contract_review"],
        reconciliation_results=state["reconciliation_results"],
        sensitive_field_review=state["sensitive_field_review"],
        test_evidence_review=state["test_evidence_review"],
        evidence_coverage_review=state["evidence_coverage_review"],
        review_pack=state["review_pack"],
        llm_reviewer_notes=state["llm_reviewer_notes"],
        trace=state["trace"],
    )
    state["artifact_paths"] = write_review_artifacts(artifacts, state["config"].output_dir)
    return state


def run_langgraph_review(config: RunConfig) -> RunResult:
    StateGraph, START, END = _load_langgraph_components()
    graph = _build_graph(StateGraph, START, END)
    state = graph.invoke({"config": config})
    trace = state["trace"]
    return RunResult(
        artifacts=state["artifact_paths"],
        notes=trace["notes"],
        trace=trace,
        status=trace["status"],
    )
