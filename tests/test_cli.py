from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.artifacts import (
    DATASET_PROFILES_FILE_NAME,
    INVENTORY_FILE_NAME,
    SCHEMA_INVENTORY_FILE_NAME,
    TRACE_FILE_NAME,
)
from data_migration_readiness_review_agent.cli import main
from data_migration_readiness_review_agent.manifest import load_manifest

FORBIDDEN_TRACE_STATUSES = {
    "ready",
    "approved",
    "compliant",
    "certified",
    "go_live_approved",
}


def manifest_data() -> dict[str, Any]:
    return {
        "migration": {
            "name": "customer_account_migration",
            "description": "Example migration pack.",
            "owner": "Example Data Migration Team",
            "source_system": "legacy_crm",
            "target_system": "new_customer_platform",
        },
        "datasets": [
            {
                "dataset_id": "customers",
                "source_path": "data/source_customers.csv",
                "target_path": "data/target_customers.csv",
                "key_columns": ["customer_id"],
                "row_count_tolerance": 0,
            }
        ],
        "mappings": [
            {
                "mapping_id": "customer_mapping",
                "dataset_id": "customers",
                "path": "mappings/customer_mapping.csv",
            }
        ],
        "contracts": [
            {
                "contract_id": "customer_contract",
                "dataset_id": "customers",
                "path": "contracts/customer_contract.yaml",
            }
        ],
        "test_results": [
            {"test_result_id": "migration_test_results", "path": "tests/test_results.csv"}
        ],
        "evidence": [
            {
                "evidence_id": "migration_notes",
                "evidence_type": "migration_notes",
                "path": "evidence/migration_notes.md",
            }
        ],
        "sensitive_field_hints": ["email", "phone"],
        "readiness_dimensions": ["scope_and_ownership"],
    }


def write_manifest(
    pack_path: Path, data: dict[str, Any] | None = None, name: str = "manifest.yaml"
) -> Path:
    manifest_path = pack_path / name
    manifest_path.write_text(json.dumps(data or manifest_data(), indent=2), encoding="utf-8")
    return manifest_path


def write_referenced_files(pack_path: Path) -> None:
    files = {
        "data/source_customers.csv": (
            "customer_id,email,phone,date_of_birth\n"
            "1,example@example.com,555-0100,1980-01-01\n"
            "2,second@example.com,555-0101,\n"
        ),
        "data/target_customers.csv": (
            "customer_id,email,phone,date_of_birth\n"
            "1,example@example.com,555-0100,1980-01-01\n"
            "2,second@example.com,555-0101,\n"
        ),
        "mappings/customer_mapping.csv": "source_field,target_field\ncustomer_id,customer_id\n",
        "contracts/customer_contract.yaml": "fields: []\n",
        "tests/test_results.csv": "test_id,status\nexample,not_assessed\n",
        "evidence/migration_notes.md": "# Notes\n",
    }
    for relative_path, content in files.items():
        path = pack_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def make_pack(tmp_path: Path, data: dict[str, Any] | None = None) -> Path:
    pack_path = tmp_path / "pack"
    pack_path.mkdir()
    write_manifest(pack_path, data)
    write_referenced_files(pack_path)
    return pack_path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cli(pack_path: Path, output_dir: Path, extra_args: list[str] | None = None) -> int:
    args = [
        "--pack",
        str(pack_path),
        "--output-dir",
        str(output_dir),
        "--no-llm",
        "--orchestrator",
        "standard",
    ]
    if extra_args:
        args.extend(extra_args)
    return main(args)


def test_cli_version_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_valid_manifest_loads(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)

    loaded = load_manifest(pack_path.resolve())

    assert loaded.data["migration"]["name"] == "customer_account_migration"
    assert loaded.manifest_path.name == "manifest.yaml"


def test_missing_manifest_exits_non_zero(tmp_path: Path) -> None:
    pack_path = tmp_path / "pack"
    pack_path.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs")

    assert exc_info.value.code != 0


def test_malformed_yaml_exits_non_zero(tmp_path: Path) -> None:
    pack_path = tmp_path / "pack"
    pack_path.mkdir()
    (pack_path / "manifest.yaml").write_text("migration: [unterminated\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs")

    assert exc_info.value.code != 0


def test_missing_required_migration_name_exits_non_zero(tmp_path: Path) -> None:
    data = manifest_data()
    del data["migration"]["name"]
    pack_path = make_pack(tmp_path, data)

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs")

    assert exc_info.value.code != 0


@pytest.mark.parametrize("datasets", [[], "customers"])
def test_datasets_must_be_non_empty_list(tmp_path: Path, datasets: Any) -> None:
    data = manifest_data()
    data["datasets"] = datasets
    pack_path = make_pack(tmp_path, data)

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs")

    assert exc_info.value.code != 0


@pytest.mark.parametrize("key_columns", [[], "customer_id", [""]])
def test_dataset_key_columns_must_be_non_empty_list(tmp_path: Path, key_columns: Any) -> None:
    data = manifest_data()
    data["datasets"][0]["key_columns"] = key_columns
    pack_path = make_pack(tmp_path, data)

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs")

    assert exc_info.value.code != 0


def test_manifest_path_cannot_escape_pack_directory(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    outside_manifest = tmp_path / "outside.yaml"
    outside_manifest.write_text(json.dumps(manifest_data()), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs", ["--manifest", str(outside_manifest)])

    assert exc_info.value.code != 0


def test_manifest_symlink_cannot_escape_pack_directory(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    outside_manifest = tmp_path / "outside.yaml"
    outside_manifest.write_text(json.dumps(manifest_data()), encoding="utf-8")
    manifest_link = pack_path / "manifest-link.yaml"
    manifest_link.symlink_to(outside_manifest)

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs", ["--manifest", "manifest-link.yaml"])

    assert exc_info.value.code != 0


def test_auto_discovered_manifest_symlink_cannot_escape_pack_directory(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "manifest.yaml").unlink()
    outside_manifest = tmp_path / "outside.yaml"
    outside_manifest.write_text(json.dumps(manifest_data()), encoding="utf-8")
    (pack_path / "manifest.yaml").symlink_to(outside_manifest)

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs")

    assert exc_info.value.code != 0


def test_referenced_file_path_cannot_escape_pack_directory(tmp_path: Path) -> None:
    data = manifest_data()
    data["datasets"][0]["source_path"] = "../outside.csv"
    pack_path = make_pack(tmp_path, data)

    with pytest.raises(SystemExit) as exc_info:
        run_cli(pack_path, tmp_path / "outputs")

    assert exc_info.value.code != 0


def test_valid_pack_writes_expected_artifacts(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    assert exit_code == 0
    assert (output_dir / INVENTORY_FILE_NAME).exists()
    assert (output_dir / DATASET_PROFILES_FILE_NAME).exists()
    assert (output_dir / SCHEMA_INVENTORY_FILE_NAME).exists()
    assert (output_dir / TRACE_FILE_NAME).exists()


def test_inventory_includes_metadata_datasets_referenced_files_and_counts(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    inventory = read_json(output_dir / INVENTORY_FILE_NAME)
    assert inventory["status"] == "inventory_created"
    assert inventory["migration"]["name"] == "customer_account_migration"
    assert inventory["datasets"][0]["dataset_id"] == "customers"
    assert inventory["datasets"][0]["status"] == "not_assessed"
    assert inventory["counts"] == {
        "datasets": 1,
        "referenced_files": 6,
        "referenced_files_present": 6,
        "referenced_files_missing": 0,
    }
    assert {item["status"] for item in inventory["referenced_files"]} == {"evidence_present"}
    assert inventory["gaps"] == []


def test_missing_referenced_files_get_gap_found_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "evidence" / "migration_notes.md").unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    inventory = read_json(output_dir / INVENTORY_FILE_NAME)
    assert exit_code == 0
    assert inventory["counts"]["referenced_files"] == 6
    assert inventory["counts"]["referenced_files_present"] == 5
    assert inventory["counts"]["referenced_files_missing"] == 1
    assert inventory["gaps"][0]["status"] == "gap_found"
    missing_file = next(
        item
        for item in inventory["referenced_files"]
        if item["path"] == "evidence/migration_notes.md"
    )
    assert missing_file["status"] == "referenced_file_missing"


def test_trace_includes_manifest_artifacts_counts_and_safe_status(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    trace = read_json(output_dir / TRACE_FILE_NAME)
    trace_text = (output_dir / TRACE_FILE_NAME).read_text(encoding="utf-8").lower()
    assert trace["manifest_path"].endswith("manifest.yaml")
    assert trace["artifacts_written"] == [
        INVENTORY_FILE_NAME,
        DATASET_PROFILES_FILE_NAME,
        SCHEMA_INVENTORY_FILE_NAME,
        TRACE_FILE_NAME,
    ]
    assert trace["counts"]["referenced_files_present"] == 6
    assert trace["dataset_profile_summary"] == {
        "datasets_profiled": 1,
        "dataset_files_expected": 2,
        "dataset_files_profiled": 2,
        "dataset_files_with_gaps": 0,
    }
    assert trace["schema_inventory_summary"] == {
        "schemas_inventoried": 1,
        "schemas_with_missing_key_columns": 0,
    }
    assert trace["no_llm"] is True
    assert trace["orchestrator"] == "standard"
    assert trace["status"] == "profile_created"
    assert not any(f'"status": "{term}"' in trace_text for term in FORBIDDEN_TRACE_STATUSES)


def test_manifest_override_works(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    default_manifest = pack_path / "manifest.yaml"
    override_manifest = pack_path / "custom_manifest.yml"
    shutil.copy(default_manifest, override_manifest)
    default_manifest.unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir, ["--manifest", "custom_manifest.yml"])

    inventory = read_json(output_dir / INVENTORY_FILE_NAME)
    assert exit_code == 0
    assert inventory["pack"]["manifest_file_name"] == "custom_manifest.yml"


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
    assert source["preview_rows"][0] == {
        "customer_id": "1",
        "email": "example@example.com",
        "phone": "555-0100",
        "date_of_birth": "1980-01-01",
    }


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
    assert schema["source"]["missing_key_columns"] == ["customer_id"]


def test_missing_dataset_csv_gets_profile_gap_without_crashing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir)

    profiles = read_json(output_dir / DATASET_PROFILES_FILE_NAME)
    source = profiles["datasets"][0]["source"]
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
    assert source["warnings"] == ["Dataset CSV file is empty: data/source_customers.csv"]


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


def test_schema_inventory_includes_columns_overlap_and_not_assessed_status(
    tmp_path: Path,
) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "data" / "source_customers.csv").write_text(
        "customer_id,email,source_only\n1,a@example.com,legacy\n", encoding="utf-8"
    )
    (pack_path / "data" / "target_customers.csv").write_text(
        "customer_id,email,target_only\n1,a@example.com,new\n", encoding="utf-8"
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    inventory = read_json(output_dir / SCHEMA_INVENTORY_FILE_NAME)
    dataset = inventory["datasets"][0]
    assert inventory["status"] == "schema_inventory_created"
    assert dataset["status"] == "not_assessed"
    assert dataset["source"]["columns"] == ["customer_id", "email", "source_only"]
    assert dataset["target"]["columns"] == ["customer_id", "email", "target_only"]
    assert dataset["schema_overlap"] == {
        "shared_columns": ["customer_id", "email"],
        "source_only_columns": ["source_only"],
        "target_only_columns": ["target_only"],
    }
    assert "ready" not in json.dumps(dataset).lower()


def test_no_llm_or_langgraph_dependencies_are_required() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8").lower()
    assert "langgraph" not in pyproject
    assert "openai" not in pyproject
    assert "pandas" not in pyproject
    assert "openpyxl" not in pyproject


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
