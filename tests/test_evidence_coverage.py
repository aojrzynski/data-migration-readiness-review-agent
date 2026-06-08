from __future__ import annotations

from pathlib import Path

from data_migration_readiness_review_agent.artifacts import EVIDENCE_COVERAGE_REVIEW_FILE_NAME
from helpers import make_pack, manifest_data, read_json, run_cli


def full_evidence_manifest() -> dict:
    data = manifest_data()
    data["evidence"] = [
        {
            "evidence_id": "migration_notes",
            "evidence_type": "migration_notes",
            "path": "evidence/migration_notes.md",
        },
        {"evidence_id": "cutover", "evidence_type": "cutover", "path": "evidence/cutover.md"},
        {"evidence_id": "rollback", "evidence_type": "rollback", "path": "evidence/rollback.md"},
        {"evidence_id": "risk", "evidence_type": "risk", "path": "evidence/risk.md"},
        {
            "evidence_id": "acceptance",
            "evidence_type": "acceptance",
            "path": "evidence/acceptance.md",
        },
    ]
    return data


def write_extra_evidence_files(pack_path: Path) -> None:
    for name in ["cutover", "rollback", "risk", "acceptance"]:
        path = pack_path / "evidence" / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n", encoding="utf-8")


def test_evidence_coverage_review_is_written_and_marks_present_types(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path, full_evidence_manifest())
    write_extra_evidence_files(pack_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = read_json(output_dir / EVIDENCE_COVERAGE_REVIEW_FILE_NAME)
    statuses = {item["evidence_type"]: item["status"] for item in review["expected_evidence_types"]}
    assert review["status"] == "evidence_coverage_review_created"
    assert set(statuses.values()) == {"evidence_present"}
    assert review["summary"]["evidence_types_present"] == 5
    assert review["summary"]["evidence_files_present"] == 5


def test_missing_expected_evidence_type_is_marked_missing(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = read_json(output_dir / EVIDENCE_COVERAGE_REVIEW_FILE_NAME)
    statuses = {item["evidence_type"]: item["status"] for item in review["expected_evidence_types"]}
    assert statuses["cutover"] == "evidence_missing"
    assert review["summary"]["evidence_types_missing"] == 4


def test_declared_missing_evidence_file_is_gap_found(tmp_path: Path) -> None:
    data = full_evidence_manifest()
    pack_path = make_pack(tmp_path, data)
    write_extra_evidence_files(pack_path)
    (pack_path / "evidence/cutover.md").unlink()
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    cutover = next(
        item
        for item in read_json(output_dir / EVIDENCE_COVERAGE_REVIEW_FILE_NAME)[
            "expected_evidence_types"
        ]
        if item["evidence_type"] == "cutover"
    )
    assert cutover["status"] == "gap_found"
    assert cutover["files_missing"] == 1


def test_extra_evidence_types_are_listed_without_failing(tmp_path: Path) -> None:
    data = full_evidence_manifest()
    data["evidence"].append(
        {"evidence_id": "other", "evidence_type": "other", "path": "evidence/other.txt"}
    )
    pack_path = make_pack(tmp_path, data)
    write_extra_evidence_files(pack_path)
    (pack_path / "evidence/other.txt").write_text("other\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = read_json(output_dir / EVIDENCE_COVERAGE_REVIEW_FILE_NAME)
    assert review["extra_evidence_types"][0]["evidence_type"] == "other"
    assert review["extra_evidence_types"][0]["status"] == "evidence_present"


def test_evidence_coverage_avoids_forbidden_approval_and_sufficiency_wording(
    tmp_path: Path,
) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review_text = (
        (output_dir / EVIDENCE_COVERAGE_REVIEW_FILE_NAME).read_text(encoding="utf-8").lower()
    )
    assert "approved" not in review_text
    assert "sufficient" not in review_text
