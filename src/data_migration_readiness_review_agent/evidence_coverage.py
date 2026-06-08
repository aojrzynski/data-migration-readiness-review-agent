from __future__ import annotations

from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.manifest import resolve_inside_pack
from data_migration_readiness_review_agent.models import LoadedManifest

EVIDENCE_COVERAGE_REVIEW_NOTE = (
    "PR #6 reviews evidence coverage only. It records declared evidence types and file "
    "presence without judging document quality."
)
EXPECTED_EVIDENCE_TYPES = ("migration_notes", "cutover", "rollback", "risk", "acceptance")


def build_evidence_coverage_review(loaded_manifest: LoadedManifest) -> dict[str, Any]:
    evidence_items = [
        item for item in loaded_manifest.data.get("evidence", []) if isinstance(item, dict)
    ]
    expected = [
        review_expected_type(loaded_manifest, evidence_items, evidence_type)
        for evidence_type in EXPECTED_EVIDENCE_TYPES
    ]
    extra = [
        review_extra_type(loaded_manifest, evidence_items, evidence_type)
        for evidence_type in sorted(
            {
                str(item.get("evidence_type"))
                for item in evidence_items
                if item.get("evidence_type") not in EXPECTED_EVIDENCE_TYPES
            }
        )
    ]
    return {
        "artifact_type": "evidence_coverage_review",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "evidence_coverage_review_created",
        "expected_evidence_types": expected,
        "extra_evidence_types": extra,
        "summary": build_summary(expected),
        "notes": [EVIDENCE_COVERAGE_REVIEW_NOTE],
    }


def review_expected_type(
    loaded_manifest: LoadedManifest, evidence_items: list[dict[str, Any]], evidence_type: str
) -> dict[str, Any]:
    matching = [item for item in evidence_items if item.get("evidence_type") == evidence_type]
    return review_items(loaded_manifest, evidence_type, matching, expected=True)


def review_extra_type(
    loaded_manifest: LoadedManifest, evidence_items: list[dict[str, Any]], evidence_type: str
) -> dict[str, Any]:
    matching = [item for item in evidence_items if item.get("evidence_type") == evidence_type]
    return review_items(loaded_manifest, evidence_type, matching, expected=False)


def review_items(
    loaded_manifest: LoadedManifest,
    evidence_type: str,
    items: list[dict[str, Any]],
    *,
    expected: bool,
) -> dict[str, Any]:
    paths: list[str] = []
    file_details: list[dict[str, Any]] = []
    files_present = 0
    files_missing = 0
    warnings: list[str] = []
    for item in items:
        relative_path = item["path"]
        paths.append(relative_path)
        resolved_path = resolve_inside_pack(
            loaded_manifest.pack_path, Path(relative_path), description=f"evidence:{evidence_type}"
        )
        present = resolved_path.exists() and resolved_path.is_file()
        if present:
            files_present += 1
        else:
            files_missing += 1
            warnings.append(f"Evidence file is missing: {relative_path}")
        file_details.append(
            {
                "path": relative_path,
                "status": "evidence_present" if present else "gap_found",
                "format": extension_format(relative_path),
                "file_size_bytes": resolved_path.stat().st_size if present else None,
            }
        )
    status = "evidence_present" if files_present else "gap_found"
    if expected and not items:
        status = "evidence_missing"
    return {
        "evidence_type": evidence_type,
        "status": status,
        "items_declared": len(items),
        "files_present": files_present,
        "files_missing": files_missing,
        "paths": paths,
        "file_details": file_details,
        "warnings": warnings,
    }


def extension_format(relative_path: str) -> str:
    suffix = Path(relative_path).suffix.casefold().lstrip(".")
    if suffix in {"md", "markdown"}:
        return "markdown"
    if suffix in {"yaml", "yml"}:
        return "yaml"
    if suffix in {"txt", "text"}:
        return "text"
    return suffix or "unknown"


def build_summary(expected: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "expected_evidence_types": len(expected),
        "evidence_types_present": sum(
            1 for item in expected if item["status"] == "evidence_present"
        ),
        "evidence_types_missing": sum(
            1 for item in expected if item["status"] == "evidence_missing"
        ),
        "evidence_types_with_gaps": sum(1 for item in expected if item["status"] == "gap_found"),
        "evidence_files_present": sum(int(item["files_present"]) for item in expected),
        "evidence_files_missing": sum(int(item["files_missing"]) for item in expected),
    }
