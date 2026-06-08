"""
Optional LLM reviewer notes. Default runs do not call an LLM; OpenAI is an optional lazy
import, model selection comes from CLI/env, outputs are parsed and checked for safe
language, and LLM failure does not block deterministic artifacts.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from data_migration_readiness_review_agent import __version__
from data_migration_readiness_review_agent.cli_constants import TOOL_NAME
from data_migration_readiness_review_agent.llm_prompt import (
    LLM_REVIEW_INSTRUCTIONS,
    build_llm_context,
)
from data_migration_readiness_review_agent.safe_language import find_forbidden_terms

LLM_REVIEW_NOTE = (
    "PR #9 adds optional LLM reviewer notes. The default run does not call an LLM. "
    "Deterministic artifacts remain authoritative."
)
LLM_SUPPLEMENTAL_NOTE = (
    "LLM notes are supplemental only. They do not change deterministic findings and do not make "
    "approval, readiness, legal, privacy, security, governance, or compliance decisions."
)

LlmCaller = Callable[[str, str, str], str]


def build_not_requested_notes(*, max_input_chars: int) -> dict[str, Any]:
    """Build the llm_reviewer_notes artifact for the default no-LLM path."""
    return {
        "artifact_type": "llm_reviewer_notes",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "llm_review_not_requested",
        "llm_requested": False,
        "provider": None,
        "model": None,
        "input_policy": _base_input_policy(max_input_chars),
        "llm_output": None,
        "warnings": [],
        "notes": [LLM_REVIEW_NOTE],
    }


def build_llm_reviewer_notes(
    *,
    review_pack: dict[str, Any],
    llm_requested: bool,
    provider: str,
    model: str | None,
    max_input_chars: int,
    llm_caller: LlmCaller | None = None,
) -> dict[str, Any]:
    """
    Build optional LLM reviewer notes or a deterministic skipped/failed/rejected
    artifact. Deterministic artifacts are already available before this runs.
    """
    if not llm_requested:
        return build_not_requested_notes(max_input_chars=max_input_chars)

    # Model selection is configuration only; do not write API keys or env values to artifacts.
    selected_model = model or os.environ.get("OPENAI_MODEL")
    input_policy = _base_input_policy(max_input_chars)
    if not selected_model:
        return _skipped_notes(
            provider=provider,
            model=None,
            input_policy=input_policy,
            warning="LLM review was requested but no model was supplied.",
        )

    # Deterministic artifacts are already built; the optional LLM receives bounded context only.
    context, input_policy = build_llm_context(review_pack, max_input_chars=max_input_chars)
    caller = llm_caller or call_openai_responses_api
    try:
        raw_text = caller(provider, selected_model, context)
    except ImportError:
        # Optional dependency failures are recorded as skipped LLM notes, not run failures.
        return _skipped_notes(
            provider=provider,
            model=selected_model,
            input_policy=input_policy,
            warning="Optional OpenAI dependency is not installed.",
        )
    except Exception as exc:  # noqa: BLE001 - optional LLM failures are artifact warnings.
        # API call failures do not block deterministic artifacts already written in memory.
        return _failed_notes(
            provider=provider,
            model=selected_model,
            input_policy=input_policy,
            warning=sanitize_llm_error(exc),
            validation={
                "json_parse_passed": False,
                "schema_validation_passed": False,
                "safe_language_passed": False,
            },
        )

    return build_notes_from_llm_text(
        raw_text,
        provider=provider,
        model=selected_model,
        input_policy=input_policy,
    )


def sanitize_llm_error(exc: Exception) -> str:
    """
    Convert provider errors into short artifact-safe messages without recording secrets
    or environment values.
    """
    message = str(exc).replace("\n", " ").replace("\r", " ")
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        # Do not write API keys or environment values into local artifacts.
        message = message.replace(api_key, "[redacted]")
    return f"LLM review call failed: {type(exc).__name__}: {message[:500]}"


def call_openai_responses_api(provider: str, model: str, context: str) -> str:
    """
    Call the optional OpenAI Responses API through a lazy import so default
    installations do not require the dependency.
    """
    if provider != "openai":
        raise ValueError(f"Unsupported LLM provider: {provider}")
    # Lazy import keeps default non-LLM runs free of optional OpenAI dependency requirements.
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(
        model=model,
        instructions=LLM_REVIEW_INSTRUCTIONS,
        input=context,
    )
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text
    return str(response)


def build_notes_from_llm_text(
    raw_text: str,
    *,
    provider: str,
    model: str,
    input_policy: dict[str, Any],
) -> dict[str, Any]:
    """
    Parse, validate, and safety-check LLM JSON before including any generated notes in
    the artifact.
    """
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return _failed_notes(
            provider=provider,
            model=model,
            input_policy=input_policy,
            warning="LLM review output was not valid JSON.",
            validation={
                "json_parse_passed": False,
                "schema_validation_passed": False,
                "safe_language_passed": False,
            },
        )

    if not validate_llm_output_shape(parsed):
        return _failed_notes(
            provider=provider,
            model=model,
            input_policy=input_policy,
            warning="LLM review output did not match the expected schema.",
            validation={
                "json_parse_passed": True,
                "schema_validation_passed": False,
                "safe_language_passed": False,
            },
        )

    unsafe_terms = find_forbidden_terms(json.dumps(parsed, sort_keys=True))
    if unsafe_terms:
        # Unsafe LLM text is rejected without storing the raw generated content.
        return _rejected_notes(
            provider=provider,
            model=model,
            input_policy=input_policy,
            warning="LLM review output contained unsafe verdict language.",
            validation={
                "json_parse_passed": True,
                "schema_validation_passed": True,
                "safe_language_passed": False,
            },
        )

    return {
        "artifact_type": "llm_reviewer_notes",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "llm_review_completed",
        "llm_requested": True,
        "provider": provider,
        "model": model,
        "input_policy": input_policy,
        "llm_output": parsed,
        "validation": {
            "json_parse_passed": True,
            "schema_validation_passed": True,
            "safe_language_passed": True,
        },
        "warnings": [],
        "notes": [LLM_SUPPLEMENTAL_NOTE],
    }


def validate_llm_output_shape(value: Any) -> bool:
    """
    Validate that optional LLM output follows the expected bounded notes shape before it
    is written.
    """
    if not isinstance(value, dict):
        return False
    if set(value) != {"summary", "observations", "suggested_human_questions", "caveats"}:
        return False
    if not isinstance(value["summary"], str):
        return False
    if not _valid_observations(value["observations"]):
        return False
    if not _valid_questions(value["suggested_human_questions"]):
        return False
    return isinstance(value["caveats"], list) and all(
        isinstance(caveat, str) for caveat in value["caveats"]
    )


def _valid_observations(value: Any) -> bool:
    """
    Private helper for valid observations used to keep deterministic artifact
    construction small and readable.
    """
    return isinstance(value, list) and all(
        isinstance(item, dict)
        and set(item) == {"category", "message", "source_finding_ids"}
        and isinstance(item["category"], str)
        and isinstance(item["message"], str)
        and _valid_string_list(item["source_finding_ids"])
        for item in value
    )


def _valid_questions(value: Any) -> bool:
    """
    Private helper for valid questions used to keep deterministic artifact construction
    small and readable.
    """
    return isinstance(value, list) and all(
        isinstance(item, dict)
        and set(item) == {"category", "question", "source_finding_ids"}
        and isinstance(item["category"], str)
        and isinstance(item["question"], str)
        and _valid_string_list(item["source_finding_ids"])
        for item in value
    )


def _valid_string_list(value: Any) -> bool:
    """
    Private helper for valid string list used to keep deterministic artifact
    construction small and readable.
    """
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _base_input_policy(max_input_chars: int) -> dict[str, Any]:
    """
    Private helper for base input policy used to keep deterministic artifact
    construction small and readable.
    """
    return {
        "source": "review_pack",
        "raw_data_rows_included": False,
        "raw_sensitive_values_included": False,
        "max_input_chars": max_input_chars,
    }


def _skipped_notes(
    *, provider: str, model: str | None, input_policy: dict[str, Any], warning: str
) -> dict[str, Any]:
    """
    Private helper for skipped notes used to keep deterministic artifact construction
    small and readable.
    """
    return {
        "artifact_type": "llm_reviewer_notes",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "llm_review_skipped",
        "llm_requested": True,
        "provider": provider,
        "model": model,
        "input_policy": input_policy,
        "llm_output": None,
        "warnings": [warning],
        "notes": [LLM_SUPPLEMENTAL_NOTE],
    }


def _failed_notes(
    *,
    provider: str,
    model: str,
    input_policy: dict[str, Any],
    warning: str,
    validation: dict[str, bool],
) -> dict[str, Any]:
    """
    Private helper for failed notes used to keep deterministic artifact construction
    small and readable.
    """
    return {
        "artifact_type": "llm_reviewer_notes",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "llm_review_failed",
        "llm_requested": True,
        "provider": provider,
        "model": model,
        "input_policy": input_policy,
        "llm_output": None,
        "validation": validation,
        "warnings": [warning],
        "notes": [LLM_SUPPLEMENTAL_NOTE],
    }


def _rejected_notes(
    *,
    provider: str,
    model: str,
    input_policy: dict[str, Any],
    warning: str,
    validation: dict[str, bool],
) -> dict[str, Any]:
    """
    Private helper for rejected notes used to keep deterministic artifact construction
    small and readable.
    """
    return {
        "artifact_type": "llm_reviewer_notes",
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "llm_review_rejected",
        "llm_requested": True,
        "provider": provider,
        "model": model,
        "input_policy": input_policy,
        "llm_output": None,
        "validation": validation,
        "warnings": [warning],
        "notes": [LLM_SUPPLEMENTAL_NOTE],
    }
