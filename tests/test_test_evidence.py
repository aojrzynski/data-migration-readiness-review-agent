from __future__ import annotations

from pathlib import Path

from data_migration_readiness_review_agent.artifacts import TEST_EVIDENCE_REVIEW_FILE_NAME
from helpers import make_pack, manifest_data, read_json, run_cli


def test_test_evidence_review_is_written_and_csv_structure_recorded(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "tests/test_results.csv").write_text(
        "test_id,status,message\nexample_test,passed,Example migration test passed\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review = read_json(output_dir / TEST_EVIDENCE_REVIEW_FILE_NAME)
    result = review["test_results"][0]
    assert review["status"] == "test_evidence_review_created"
    assert result["headers"] == ["test_id", "status", "message"]
    assert result["row_count"] == 1
    assert result["status_column"] == "status"
    assert result["status_counts"] == {"passed": 1}
    assert result["passed_like_count"] == 1


def test_failed_and_warning_rows_are_counted_and_summarized(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "tests/test_results.csv").write_text(
        "test_id,status,message,raw_value\n"
        "t1,failed,Bad row,secret1\n"
        "t2,warning,Check manually,secret2\n"
        "t3,error,Boom,secret3\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    result = read_json(output_dir / TEST_EVIDENCE_REVIEW_FILE_NAME)["test_results"][0]
    assert result["failed_like_count"] == 2
    assert result["warning_like_count"] == 1
    assert len(result["failed_or_warning_samples"]) == 3
    assert result["failed_or_warning_samples"][0] == {
        "row_number": 2,
        "test_id": "t1",
        "status": "failed",
        "message": "Bad row",
    }
    assert "raw_value" not in result["failed_or_warning_samples"][0]


def test_failed_warning_samples_are_bounded_to_50(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    rows = ["test_id,status,message"] + [f"t{i},failed,Failure {i}" for i in range(60)]
    (pack_path / "tests/test_results.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    result = read_json(output_dir / TEST_EVIDENCE_REVIEW_FILE_NAME)["test_results"][0]
    assert result["failed_like_count"] == 60
    assert len(result["failed_or_warning_samples"]) == 50


def test_missing_test_result_file_records_gap(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    (pack_path / "tests/test_results.csv").unlink()
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    result = read_json(output_dir / TEST_EVIDENCE_REVIEW_FILE_NAME)["test_results"][0]
    assert result["status"] == "gap_found"
    assert result["warnings"]


def test_non_csv_test_evidence_is_reviewed_without_deep_parsing(tmp_path: Path) -> None:
    data = manifest_data()
    data["test_results"] = [{"test_result_id": "notes", "path": "tests/test_notes.md"}]
    pack_path = make_pack(tmp_path, data)
    (pack_path / "tests/test_notes.md").write_text("# Test notes\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    result = read_json(output_dir / TEST_EVIDENCE_REVIEW_FILE_NAME)["test_results"][0]
    assert result["status"] == "reviewed"
    assert result["format"] == "markdown"
    assert "headers" not in result


def test_test_evidence_review_avoids_forbidden_go_live_and_approval_wording(tmp_path: Path) -> None:
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    run_cli(pack_path, output_dir)

    review_text = (output_dir / TEST_EVIDENCE_REVIEW_FILE_NAME).read_text(encoding="utf-8").lower()
    assert "go_live_approved" not in review_text
    assert "go-live approved" not in review_text
    assert "approved" not in review_text
