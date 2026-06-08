from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent.artifacts import LLM_REVIEWER_NOTES_FILE_NAME
from data_migration_readiness_review_agent.cli import main
from data_migration_readiness_review_agent.llm_prompt import build_llm_context
from data_migration_readiness_review_agent.llm_review import (
    build_llm_reviewer_notes,
    build_notes_from_llm_text,
    validate_llm_output_shape,
)
from helpers import make_pack, read_json


def valid_llm_output() -> dict[str, Any]:
    return {
        "summary": "Supplemental notes highlight items a human reviewer may inspect.",
        "observations": [
            {
                "category": "reconciliation",
                "message": "A deterministic reconciliation finding is present for review.",
                "source_finding_ids": ["reconciliation:customers:row_count"],
            }
        ],
        "suggested_human_questions": [
            {
                "category": "mapping",
                "question": "Which owner can confirm the mapped customer fields?",
                "source_finding_ids": ["mapping:customers:missing_target"],
            }
        ],
        "caveats": ["These notes are supplemental and limited to supplied review-pack evidence."],
    }


def minimal_review_pack() -> dict[str, Any]:
    return {
        "migration": {"name": "unit_migration", "owner": "team"},
        "source_artifacts": ["review_pack.json"],
        "summary": {"total_findings": 60},
        "sections": [{"category": "mapping", "finding_count": 60}],
        "findings": [
            {
                "finding_id": f"finding-{index}",
                "category": "mapping",
                "status": "warning",
                "severity": "medium",
                "message": f"Finding {index} needs human review.",
                "source_artifact": "mapping_review.json",
            }
            for index in range(60)
        ],
        "follow_up_checklist": [
            {"finding_id": f"finding-{index}", "question": f"Question {index}?"}
            for index in range(60)
        ],
    }


def test_valid_llm_output_parser_and_validator() -> None:
    output = valid_llm_output()

    assert validate_llm_output_shape(output) is True

    notes = build_notes_from_llm_text(
        json.dumps(output),
        provider="openai",
        model="unit-test-model",
        input_policy={"source": "review_pack", "max_input_chars": 20000},
    )

    assert notes["status"] == "llm_review_completed"
    assert notes["llm_output"] == output
    assert notes["validation"] == {
        "json_parse_passed": True,
        "schema_validation_passed": True,
        "safe_language_passed": True,
    }


def test_invalid_json_fails_without_including_raw_text() -> None:
    notes = build_notes_from_llm_text(
        "not-json with private raw content",
        provider="openai",
        model="unit-test-model",
        input_policy={"source": "review_pack", "max_input_chars": 20000},
    )

    assert notes["status"] == "llm_review_failed"
    assert notes["llm_output"] is None
    assert "not-json" not in json.dumps(notes)


def test_invalid_schema_fails() -> None:
    notes = build_notes_from_llm_text(
        json.dumps({"summary": "missing arrays"}),
        provider="openai",
        model="unit-test-model",
        input_policy={"source": "review_pack", "max_input_chars": 20000},
    )

    assert notes["status"] == "llm_review_failed"
    assert notes["validation"]["schema_validation_passed"] is False


def test_unsafe_positive_verdict_wording_is_rejected() -> None:
    output = valid_llm_output()
    output["summary"] = "The migration is ready."

    notes = build_notes_from_llm_text(
        json.dumps(output),
        provider="openai",
        model="unit-test-model",
        input_policy={"source": "review_pack", "max_input_chars": 20000},
    )

    assert notes["status"] == "llm_review_rejected"
    assert notes["llm_output"] is None
    assert notes["validation"]["safe_language_passed"] is False


def test_build_llm_reviewer_notes_records_fake_safe_output() -> None:
    notes = build_llm_reviewer_notes(
        review_pack=minimal_review_pack(),
        llm_requested=True,
        provider="openai",
        model="unit-test-model",
        max_input_chars=20000,
        llm_caller=lambda _provider, _model, _context: json.dumps(valid_llm_output()),
    )

    assert notes["status"] == "llm_review_completed"
    assert notes["llm_output"]["observations"]
    assert notes["llm_output"]["suggested_human_questions"]
    assert notes["llm_output"]["caveats"]


def test_llm_context_uses_review_pack_caps_and_excludes_raw_csv_values() -> None:
    context, policy = build_llm_context(minimal_review_pack(), max_input_chars=20000)
    parsed = json.loads(context)

    assert parsed["findings"][-1]["finding_id"] == "finding-49"
    assert parsed["follow_up_checklist"][-1]["finding_id"] == "finding-49"
    assert "example@example.com" not in context
    assert "555-0100" not in context
    assert policy["max_findings_sent"] == 50
    assert policy["max_follow_up_items_sent"] == 50
    assert policy["input_truncated"] is False


def test_llm_context_truncation_is_recorded() -> None:
    context, policy = build_llm_context(minimal_review_pack(), max_input_chars=100)

    assert len(context) == 100
    assert policy["input_truncated"] is True
    assert policy["original_context_char_count"] > policy["sent_context_char_count"]


def test_default_cli_writes_not_requested_llm_artifact_without_openai_or_key(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pack_path = make_pack(tmp_path)
    output_dir = tmp_path / "outputs"

    assert main(["--pack", str(pack_path), "--output-dir", str(output_dir), "--no-llm"]) == 0

    notes = read_json(output_dir / LLM_REVIEWER_NOTES_FILE_NAME)
    assert notes["status"] == "llm_review_not_requested"
    assert notes["llm_requested"] is False
    assert notes["input_policy"]["raw_data_rows_included"] is False
