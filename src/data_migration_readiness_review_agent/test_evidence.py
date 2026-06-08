"""
Reviews structural test evidence. It parses CSV result files for status counts and
bounded failed/warning samples, records non-CSV metadata, and does not judge test
sufficiency.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.manifest import resolve_inside_pack
from data_migration_readiness_review_agent.models import LoadedManifest

TEST_EVIDENCE_REVIEW_NOTE = (
    "PR #6 reviews supplied test evidence structure only. It records supplied files without "
    "deciding launch suitability."
)

ID_COLUMNS = ("test_id", "test_name", "check", "name")
STATUS_COLUMNS = ("status", "result", "outcome")
MESSAGE_COLUMNS = ("message", "details", "detail")
FAILED_LIKE = {"fail", "failed", "error", "errored"}
WARNING_LIKE = {"warning", "warn"}
PASSED_LIKE = {"pass", "passed", "success", "succeeded"}
# Samples are bounded so evidence artifacts do not become copied result files.
SAMPLE_LIMIT = 50


def build_test_evidence_review(loaded_manifest: LoadedManifest) -> dict[str, Any]:
    """
    Build test_evidence_review.json by structurally summarizing declared test evidence
    and bounded failed or warning examples.
    """
    reviews = [
        review_test_result(loaded_manifest, entry)
        for entry in loaded_manifest.data.get("test_results", [])
    ]
    return {
        "artifact_type": "test_evidence_review",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "test_evidence_review_created",
        "test_results": reviews,
        "summary": build_summary(reviews),
        "notes": [TEST_EVIDENCE_REVIEW_NOTE],
    }


def review_test_result(loaded_manifest: LoadedManifest, entry: dict[str, Any]) -> dict[str, Any]:
    """Review one declared test result file and dispatch CSV files to structural parsing."""
    relative_path = entry["path"]
    test_result_id = entry.get("test_result_id", relative_path)
    resolved_path = resolve_inside_pack(
        loaded_manifest.pack_path, Path(relative_path), description=f"test_result:{test_result_id}"
    )
    base: dict[str, Any] = {
        "test_result_id": test_result_id,
        "path": relative_path,
        "status": "reviewed",
        "format": extension_format(relative_path),
        "file_size_bytes": None,
        "warnings": [],
    }
    if not resolved_path.exists() or not resolved_path.is_file():
        # Missing test evidence is a gap, not a fatal run error.
        base["status"] = "gap_found"
        base["warnings"].append(f"Test result file is missing: {relative_path}")
        return base
    base["file_size_bytes"] = resolved_path.stat().st_size
    if base["format"] == "csv":
        return review_csv_test_result(resolved_path, base)
    return base


def extension_format(relative_path: str) -> str:
    """Return the normalized file format label used in review artifacts."""
    suffix = Path(relative_path).suffix.casefold().lstrip(".")
    if suffix in {"yaml", "yml"}:
        return "yaml"
    if suffix in {"md", "markdown"}:
        return "markdown"
    if suffix in {"txt", "text"}:
        return "text"
    return suffix or "unknown"


def review_csv_test_result(path: Path, base: dict[str, Any]) -> dict[str, Any]:
    """
    Parse one CSV test result file, detect a status column, classify statuses, and keep
    bounded row summaries.
    """
    base.update(
        {
            "headers": [],
            "row_count": 0,
            "id_column": None,
            "status_column": None,
            "message_column": None,
            "status_counts": {},
            "failed_like_count": 0,
            "warning_like_count": 0,
            "passed_like_count": 0,
            "failed_or_warning_samples": [],
        }
    )
    try:
        with path.open("r", encoding="utf-8", newline="") as file_obj:
            reader = csv.DictReader(file_obj, strict=True)
            if reader.fieldnames is None:
                base["status"] = "failed_check"
                base["warnings"].append("CSV test result file has no header row.")
                return base
            headers = [header or "" for header in reader.fieldnames]
            base["headers"] = headers
            id_column = first_present(headers, ID_COLUMNS)
            status_column = first_present(headers, STATUS_COLUMNS)
            message_column = first_present(headers, MESSAGE_COLUMNS)
            base["id_column"] = id_column
            base["status_column"] = status_column
            base["message_column"] = message_column
            counts: Counter[str] = Counter()
            samples: list[dict[str, Any]] = []
            for row_number, row in enumerate(reader, start=2):
                base["row_count"] += 1
                status = normalized_cell(row, status_column)
                if status_column is not None:
                    counts[status.casefold()] += 1
                status_key = status.casefold()
                if status_key in FAILED_LIKE:
                    base["failed_like_count"] += 1
                if status_key in WARNING_LIKE:
                    base["warning_like_count"] += 1
                if status_key in PASSED_LIKE:
                    base["passed_like_count"] += 1
                if status_key in FAILED_LIKE | WARNING_LIKE and len(samples) < SAMPLE_LIMIT:
                    # Keep a small set of examples; counts still summarize the whole file.
                    samples.append(
                        build_row_summary(row_number, row, id_column, status_column, message_column)
                    )
            base["status_counts"] = dict(sorted(counts.items()))
            base["failed_or_warning_samples"] = samples
    except (csv.Error, OSError, UnicodeDecodeError) as exc:
        base["status"] = "failed_check"
        base["warnings"].append(f"CSV test result file could not be parsed: {exc}")
    return base


def first_present(headers: list[str], candidates: tuple[str, ...]) -> str | None:
    """Return the first candidate column name that appears in the CSV headers."""
    folded = {header.casefold(): header for header in headers}
    for candidate in candidates:
        if candidate in folded:
            return folded[candidate]
    return None


def normalized_cell(row: dict[str, str | None], column: str | None) -> str:
    """Return a stripped cell value for a selected column, or an empty string when absent."""
    if column is None:
        return ""
    return (row.get(column) or "").strip()


def build_row_summary(
    row_number: int,
    row: dict[str, str | None],
    id_column: str | None,
    status_column: str | None,
    message_column: str | None,
) -> dict[str, Any]:
    """Build the bounded row summary used for failed or warning-like CSV test rows."""
    # Include selected identifying/status columns only, not the full evidence row.
    summary: dict[str, Any] = {"row_number": row_number}
    if id_column is not None:
        summary[id_column] = normalized_cell(row, id_column)
    if status_column is not None:
        summary[status_column] = normalized_cell(row, status_column)
    if message_column is not None:
        summary[message_column] = normalized_cell(row, message_column)[:200]
    return summary


def build_summary(reviews: list[dict[str, Any]]) -> dict[str, int]:
    """Build compact summary counts for the artifact currently being assembled."""
    return {
        "test_results_expected": len(reviews),
        "test_results_reviewed": sum(1 for review in reviews if review["status"] == "reviewed"),
        "test_result_files_with_gaps": sum(
            1 for review in reviews if review["status"] == "gap_found"
        ),
        "csv_test_rows_reviewed": sum(int(review.get("row_count", 0)) for review in reviews),
        "failed_like_rows": sum(int(review.get("failed_like_count", 0)) for review in reviews),
        "warning_like_rows": sum(int(review.get("warning_like_count", 0)) for review in reviews),
    }
