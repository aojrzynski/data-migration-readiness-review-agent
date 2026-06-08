from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from data_migration_readiness_review_agent.manifest import load_manifest
from helpers import make_pack, manifest_data, run_cli


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


def test_manifest_override_works(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    default_manifest = pack_path / "manifest.yaml"
    override_manifest = pack_path / "custom_manifest.yml"
    shutil.copy(default_manifest, override_manifest)
    default_manifest.unlink()
    output_dir = tmp_path / "outputs"

    exit_code = run_cli(pack_path, output_dir, ["--manifest", "custom_manifest.yml"])

    inventory = json.loads((output_dir / "migration_inventory.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert inventory["pack"]["manifest_file_name"] == "custom_manifest.yml"
