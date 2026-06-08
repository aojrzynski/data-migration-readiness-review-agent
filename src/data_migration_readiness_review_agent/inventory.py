"""
Builds migration_inventory.json from manifest references. Inventory records file
presence and lightweight metadata only; deeper data checks happen in downstream
artifacts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.manifest import resolve_inside_pack
from data_migration_readiness_review_agent.models import FileReference, LoadedManifest

INVENTORY_NOTE = (
    "PR #3 includes manifest and file inventory before dataset profiling. It does not compare "
    "records, run reconciliation, call an LLM, or assess readiness."
)


def build_inventory(loaded_manifest: LoadedManifest) -> dict[str, Any]:
    """
    Build migration_inventory.json from manifest declarations. The output is
    deterministic file metadata and gap records, not a data-content review.
    """
    manifest = loaded_manifest.data
    references = collect_file_references(manifest)
    # Inventory checks file presence and metadata only; it does not parse file contents.
    referenced_files = [
        inspect_file_reference(loaded_manifest.pack_path, ref) for ref in references
    ]
    # Missing referenced files are collected as gaps for later human review.
    gaps = [
        build_missing_file_gap(file_info)
        for file_info in referenced_files
        if file_info["status"] != "evidence_present"
    ]
    present_count = sum(
        1 for file_info in referenced_files if file_info["status"] == "evidence_present"
    )
    counts = {
        "datasets": len(manifest["datasets"]),
        "referenced_files": len(referenced_files),
        "referenced_files_present": present_count,
        "referenced_files_missing": len(referenced_files) - present_count,
    }

    return {
        "artifact_type": "migration_inventory",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "inventory_created",
        "migration": dict(manifest["migration"]),
        "pack": {
            "pack_path": str(loaded_manifest.pack_path),
            "manifest_path": str(loaded_manifest.manifest_path),
            "manifest_file_name": loaded_manifest.manifest_path.name,
        },
        "counts": counts,
        "datasets": [build_dataset_entry(dataset) for dataset in manifest["datasets"]],
        "referenced_files": referenced_files,
        "sensitive_field_hints": list(manifest.get("sensitive_field_hints", [])),
        "readiness_dimensions": list(manifest.get("readiness_dimensions", [])),
        "gaps": gaps,
        "notes": [INVENTORY_NOTE],
    }


def build_dataset_entry(dataset: dict[str, Any]) -> dict[str, Any]:
    """Copy the manifest dataset fields that belong in migration_inventory.json."""
    entry = {
        "dataset_id": dataset["dataset_id"],
        "source_path": dataset["source_path"],
        "target_path": dataset["target_path"],
        "key_columns": list(dataset["key_columns"]),
        "status": "not_assessed",
    }
    if "row_count_tolerance" in dataset:
        entry["row_count_tolerance"] = dataset["row_count_tolerance"]
    return entry


def collect_file_references(manifest: dict[str, Any]) -> list[FileReference]:
    """Collect every manifest-declared file path that inventory should check for presence."""
    references: list[FileReference] = []
    for dataset in manifest["datasets"]:
        dataset_id = dataset["dataset_id"]
        references.append(
            FileReference(
                reference_id=f"dataset:{dataset_id}:source",
                category="dataset_source",
                dataset_id=dataset_id,
                path=dataset["source_path"],
            )
        )
        references.append(
            FileReference(
                reference_id=f"dataset:{dataset_id}:target",
                category="dataset_target",
                dataset_id=dataset_id,
                path=dataset["target_path"],
            )
        )

    for mapping in manifest.get("mappings", []):
        references.append(
            FileReference(
                reference_id=f"mapping:{mapping.get('mapping_id', mapping['path'])}",
                category="mapping",
                dataset_id=mapping.get("dataset_id"),
                path=mapping["path"],
            )
        )
    for contract in manifest.get("contracts", []):
        references.append(
            FileReference(
                reference_id=f"contract:{contract.get('contract_id', contract['path'])}",
                category="contract",
                dataset_id=contract.get("dataset_id"),
                path=contract["path"],
            )
        )
    for test_result in manifest.get("test_results", []):
        test_result_id = test_result.get("test_result_id", test_result["path"])
        references.append(
            FileReference(
                reference_id=f"test_result:{test_result_id}",
                category="test_result",
                path=test_result["path"],
            )
        )
    for evidence in manifest.get("evidence", []):
        evidence_id = evidence.get("evidence_id", evidence["path"])
        evidence_type = evidence.get("evidence_type", "evidence")
        references.append(
            FileReference(
                reference_id=f"evidence:{evidence_id}",
                category=f"evidence_{evidence_type}",
                path=evidence["path"],
            )
        )
    return references


def inspect_file_reference(pack_path: Path, reference: FileReference) -> dict[str, Any]:
    """Resolve one manifest file reference and return local file metadata when it exists."""
    resolved = resolve_inside_pack(
        pack_path, Path(reference.path), description=reference.reference_id
    )
    exists = resolved.exists()
    is_file = resolved.is_file() if exists else False
    status = "evidence_present" if exists and is_file else "referenced_file_missing"
    return {
        "reference_id": reference.reference_id,
        "category": reference.category,
        "dataset_id": reference.dataset_id,
        "path": reference.path,
        "resolved_relative_path": str(resolved.relative_to(pack_path)),
        "exists": exists,
        "is_file": is_file,
        "extension": resolved.suffix,
        "size_bytes": resolved.stat().st_size if exists and is_file else None,
        "safe_status": "referenced_file_present"
        if exists and is_file
        else "referenced_file_missing",
        "status": status,
    }


def build_missing_file_gap(file_info: dict[str, Any]) -> dict[str, str]:
    """Create the inventory gap entry for one missing manifest-referenced file."""
    return {
        "gap_id": f"missing_file:{file_info['reference_id']}",
        "status": "gap_found",
        "message": f"Referenced file is missing: {file_info['path']}",
    }
