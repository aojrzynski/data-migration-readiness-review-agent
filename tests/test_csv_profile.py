from __future__ import annotations

from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent.artifacts import (
    DATASET_PROFILES_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    TRACE_FILE_NAME,
)
from helpers import make_pack, read_json, run_cli


def column_by_name(profile_side: dict[str, Any], name: str) -> dict[str, Any]:
    return next(column for column in profile_side["columns"] if column["name"] == name)


def test_csv_profile_captures_counts_types_nulls_distincts_and_bounded_preview(
    tmp_path: Path,
) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text(
        "customer_id,email,phone,date_of_birth\n"
        "1,example@example.com,555-0100,1980-01-01\n"
        "2,second@example.com,555-0101,\n"
        "3,third@example.com,555-0102,NULL\n"
        "4,fourth@example.com,555-0103,1981-02-03\n"
        "5,fifth@example.com,555-0104,1982-03-04\n"
        "6,sixth@example.com,555-0105,1983-04-05\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    profiles = read_json(output_dir / DATASET_PROFILES_FILE_NAME)
    source = profiles["datasets"][0]["source"]
    customer_id = column_by_name(source, "customer_id")
    date_of_birth = column_by_name(source, "date_of_birth")
    assert profiles["status"] == "profile_created"
    assert source["status"] == "profile_created"
    assert source["row_count"] == 6
    assert source["column_count"] == 4
    assert source["key_columns_present"] is True
    assert source["missing_key_columns"] == []
    assert customer_id["position"] == 1
    assert customer_id["inferred_type"] == "integer"
    assert customer_id["null_count"] == 0
    assert customer_id["null_rate"] == 0.0
    assert customer_id["non_null_count"] == 6
    assert customer_id["distinct_count"] == 6
    assert customer_id["distinct_count_capped"] is False
    assert date_of_birth["inferred_type"] == "date"
    assert date_of_birth["null_count"] == 2
    assert date_of_birth["null_rate"] == 0.333333
    assert len(source["preview_rows"]) == 5


def test_duplicate_key_count_is_calculated_within_each_csv(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text(
        "customer_id,email\n1,a@example.com\n1,b@example.com\n1,c@example.com\n2,d@example.com\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    source = read_json(output_dir / DATASET_PROFILES_FILE_NAME)["datasets"][0]["source"]
    assert source["duplicate_key_count"] == 2


def test_missing_key_columns_warn_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text(
        "email\na@example.com\n", encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    source = read_json(output_dir / DATASET_PROFILES_FILE_NAME)["datasets"][0]["source"]
    schema = read_json(output_dir / SCHEMA_INVENTORY_FILE_NAME)["datasets"][0]
    assert exit_code == 0
    assert source["status"] == "profile_created"
    assert source["key_columns_present"] is False
    assert source["missing_key_columns"] == ["customer_id"]
    assert "missing key column" in source["warnings"][0]
    assert schema["source"]["key_columns_present"] is False


def test_missing_dataset_csv_gets_profile_gap_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    source = read_json(output_dir / DATASET_PROFILES_FILE_NAME)["datasets"][0]["source"]
    trace = read_json(output_dir / TRACE_FILE_NAME)
    assert exit_code == 0
    assert source["status"] == "gap_found"
    assert source["warnings"] == ["Dataset CSV file is missing: data/source_customers.csv"]
    assert trace["dataset_profile_summary"]["dataset_files_with_gaps"] == 1


def test_empty_csv_gets_profile_gap_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text("", encoding="utf-8")
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    source = read_json(output_dir / DATASET_PROFILES_FILE_NAME)["datasets"][0]["source"]
    assert exit_code == 0
    assert source["status"] == "gap_found"


def test_malformed_csv_records_failed_check_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text(
        'customer_id,email\n1,"unterminated\n', encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    source = read_json(output_dir / DATASET_PROFILES_FILE_NAME)["datasets"][0]["source"]
    assert exit_code == 0
    assert source["status"] == "failed_check"
    assert "could not be profiled" in source["warnings"][0]


def test_duplicate_column_names_emit_warning(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text(
        "customer_id,email,email\n1,a@example.com,alternate@example.com\n", encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    source = read_json(output_dir / DATASET_PROFILES_FILE_NAME)["datasets"][0]["source"]
    assert source["status"] == "profile_created"
    assert "duplicate column names: email" in source["warnings"][0]
