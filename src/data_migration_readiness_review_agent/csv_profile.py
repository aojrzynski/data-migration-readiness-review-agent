"""
Profiles manifest-declared CSV source and target files with the standard library csv
module. It records bounded previews, aggregate statistics, duplicate key counts, and
gaps without dumping full datasets.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.manifest import resolve_inside_pack
from data_migration_readiness_review_agent.models import LoadedManifest

PROFILE_NOTE = (
    "PR #3 profiles CSV datasets only. It does not compare mapped fields, run "
    "reconciliation, call an LLM, or assess readiness. Distinct counts are capped at "
    "1000 stored values per column."
)

# Bounded caps prevent artifacts from becoming dataset dumps.
DISTINCT_VALUE_CAP = 1000
PREVIEW_ROW_LIMIT = 5
PREVIEW_COLUMN_LIMIT = 25
NULL_VALUES = {"", "NULL", "null", "None", "none", "N/A", "n/a", "NA", "na"}
BOOLEAN_VALUES = {"true", "false", "yes", "no", "y", "n"}


@dataclass
class ColumnAccumulator:
    """
    In-memory column statistics while profiling one CSV file; it keeps aggregate counts
    and bounded distinct tracking rather than full column values.
    """
    name: str
    position: int
    null_count: int = 0
    non_null_count: int = 0
    distinct_values: set[str] = field(default_factory=set)
    distinct_count_capped: bool = False
    observed_types: set[str] = field(default_factory=set)

    def add_value(self, value: str) -> None:
        """Add one CSV cell value to aggregate counters without storing the full column."""
        if is_null_value(value):
            self.null_count += 1
            return

        normalized = value.strip()
        self.non_null_count += 1
        if not self.distinct_count_capped:
            if len(self.distinct_values) < DISTINCT_VALUE_CAP:
                self.distinct_values.add(normalized)
            elif normalized not in self.distinct_values:
                # Once the cap is reached, record that exact distinct counts are bounded.
                self.distinct_count_capped = True
        self.observed_types.add(detect_value_type(normalized))

    def to_profile(self, row_count: int) -> dict[str, Any]:
        """
        Render accumulated column statistics into the dataset_profiles.json shape.
        """
        return {
            "name": self.name,
            "position": self.position,
            "inferred_type": infer_column_type(self.observed_types),
            "null_count": self.null_count,
            "null_rate": round(self.null_count / row_count, 6) if row_count else 0.0,
            "non_null_count": self.non_null_count,
            "distinct_count": len(self.distinct_values),
            "distinct_count_capped": self.distinct_count_capped,
        }


def build_dataset_profiles(loaded_manifest: LoadedManifest) -> dict[str, Any]:
    """
    Build dataset_profiles.json for source and target CSVs declared in the manifest.
    Missing or invalid files become gaps or failed checks instead of stopping unrelated
    datasets.
    """
    datasets = [
        profile_dataset(loaded_manifest.pack_path, dataset)
        for dataset in loaded_manifest.data["datasets"]
    ]
    return {
        "artifact_type": "dataset_profiles",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "profile_created",
        "profile_scope": "csv_dataset_headers_and_column_statistics",
        "datasets": datasets,
        "notes": [PROFILE_NOTE],
    }


def profile_dataset(pack_path: Path, dataset: dict[str, Any]) -> dict[str, Any]:
    """
    Profile one manifest dataset entry by locating its source and target CSV files and
    preserving dataset context in the output.
    """
    key_columns = list(dataset["key_columns"])
    return {
        "dataset_id": dataset["dataset_id"],
        "key_columns": key_columns,
        "source": profile_csv_file(pack_path, dataset["source_path"], key_columns),
        "target": profile_csv_file(pack_path, dataset["target_path"], key_columns),
    }


def profile_csv_file(pack_path: Path, relative_path: str, key_columns: list[str]) -> dict[str, Any]:
    """
    Read one CSV file and compute bounded structural statistics, previews, inferred
    types, and duplicate key counts.
    """
    resolved_path = resolve_inside_pack(pack_path, Path(relative_path), description=relative_path)
    base_profile: dict[str, Any] = {
        "path": relative_path,
        "status": "profile_created",
        "format": "csv",
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "duplicate_key_count": 0,
        "key_columns": key_columns,
        "key_columns_present": False,
        "missing_key_columns": list(key_columns),
        "preview_rows": [],
        "warnings": [],
    }

    if not resolved_path.exists() or not resolved_path.is_file():
        # A missing CSV is evidence to report, not a reason to stop the whole run.
        base_profile["status"] = "gap_found"
        base_profile["warnings"].append(f"Dataset CSV file is missing: {relative_path}")
        return base_profile

    try:
        with resolved_path.open("r", encoding="utf-8", newline="") as file_obj:
            rows = csv.reader(file_obj, strict=True)
            try:
                headers = next(rows)
            except StopIteration:
                # Empty files are recorded as gaps so other datasets can still be reviewed.
                base_profile["status"] = "gap_found"
                base_profile["warnings"].append(f"Dataset CSV file is empty: {relative_path}")
                return base_profile

            if not headers or all(not header.strip() for header in headers):
                base_profile["status"] = "gap_found"
                base_profile["warnings"].append(
                    f"Dataset CSV file has no header row: {relative_path}"
                )
                return base_profile

            duplicate_columns = find_duplicate_headers(headers)
            warnings = list(base_profile["warnings"])
            if duplicate_columns:
                warnings.append(
                    "Dataset CSV header has duplicate column names: " + ", ".join(duplicate_columns)
                )

            accumulators = [
                ColumnAccumulator(name=header, position=index + 1)
                for index, header in enumerate(headers)
            ]
            key_columns_present = all(column in headers for column in key_columns)
            missing_key_columns = [column for column in key_columns if column not in headers]
            if missing_key_columns:
                warnings.append(
                    "Dataset CSV is missing key column(s): " + ", ".join(missing_key_columns)
                )

            row_count = 0
            duplicate_key_count = 0
            seen_keys: set[tuple[str, ...]] = set()
            for row in rows:
                row_count += 1
                normalized_row = normalize_row_length(row, len(headers))
                row_dict = dict(zip(headers, normalized_row, strict=True))
                for accumulator, value in zip(accumulators, normalized_row, strict=True):
                    accumulator.add_value(value)
                if row_count <= PREVIEW_ROW_LIMIT:
                    # Preview rows and columns are capped to show shape without exposing full data.
                    base_profile["preview_rows"].append(build_preview_row(headers, normalized_row))
                if key_columns_present:
                    # Duplicate key counting uses manifest keys as structural evidence only.
                    key_value = tuple(row_dict[column] for column in key_columns)
                    if key_value in seen_keys:
                        duplicate_key_count += 1
                    else:
                        seen_keys.add(key_value)
    except (csv.Error, OSError, UnicodeDecodeError) as exc:
        # Malformed or unreadable CSVs are failed checks instead of run-stopping errors.
        base_profile["status"] = "failed_check"
        base_profile["warnings"].append(f"Dataset CSV could not be profiled: {exc}")
        return base_profile

    base_profile.update(
        {
            "row_count": row_count,
            "column_count": len(headers),
            "columns": [accumulator.to_profile(row_count) for accumulator in accumulators],
            "duplicate_key_count": duplicate_key_count,
            "key_columns_present": key_columns_present,
            "missing_key_columns": missing_key_columns,
            "warnings": warnings,
        }
    )
    return base_profile


def normalize_row_length(row: list[str], expected_length: int) -> list[str]:
    """Pad or trim a CSV row so it lines up with the header length."""
    if len(row) < expected_length:
        return [*row, *([""] * (expected_length - len(row)))]
    return row[:expected_length]


def build_preview_row(headers: list[str], row: list[str]) -> dict[str, str]:
    """Build a capped preview row so profiles show file shape without copying the whole dataset."""
    # Cap preview columns independently from row caps to keep wide files manageable.
    preview_headers = headers[:PREVIEW_COLUMN_LIMIT]
    preview_values = row[:PREVIEW_COLUMN_LIMIT]
    return dict(zip(preview_headers, preview_values, strict=True))


def find_duplicate_headers(headers: list[str]) -> list[str]:
    """Return duplicate CSV header names while preserving first-seen order."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for header in headers:
        if header in seen and header not in duplicates:
            duplicates.append(header)
        seen.add(header)
    return duplicates


def is_null_value(value: str) -> bool:
    """Return True for blank or configured null-like CSV values."""
    # Null tokens are normalized before type inference so blanks do not look like text.
    return value.strip() in NULL_VALUES


def detect_value_type(value: str) -> str:
    """Infer the primitive type of one non-null CSV cell using simple deterministic rules."""
    lower_value = value.lower()
    # Type inference checks structured types before falling back to text.
    if lower_value in BOOLEAN_VALUES:
        return "boolean"
    if is_integer(value):
        return "integer"
    if is_decimal(value):
        return "decimal"
    if is_datetime(value):
        return "datetime"
    if is_date(value):
        return "date"
    return "text"


def infer_column_type(observed_types: set[str]) -> str:
    """Collapse observed per-cell types into one column-level inferred type."""
    if not observed_types:
        return "empty"
    if observed_types == {"integer"}:
        return "integer"
    if observed_types <= {"integer", "decimal"}:
        return "decimal" if "decimal" in observed_types else "integer"
    if len(observed_types) == 1:
        return next(iter(observed_types))
    return "mixed"


def is_integer(value: str) -> bool:
    """Return True when a CSV cell can be read as an integer."""
    if value.startswith(("+", "-")):
        return value[1:].isdecimal()
    return value.isdecimal()


def is_decimal(value: str) -> bool:
    """Return True when a CSV cell can be read as a decimal number."""
    try:
        Decimal(value)
    except InvalidOperation:
        return False
    return True


def is_date(value: str) -> bool:
    """Return True when a CSV cell matches an ISO date."""
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def is_datetime(value: str) -> bool:
    """Return True when a CSV cell matches an ISO datetime."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return "T" in value or " " in value
