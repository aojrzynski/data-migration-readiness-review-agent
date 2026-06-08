from __future__ import annotations

import re

FORBIDDEN_VERDICT_PHRASES = (
    "go_live_approved",
    "go-live approved",
    "go live approved",
    "go_live_ready",
    "go-live ready",
    "ready for go-live",
    "safe to migrate",
    "migration is ready",
    "readiness score",
    "approved",
    "certified",
    "compliant",
)

_VERDICT_PATTERN = r"approve|approved|certify|certified|compliant|go-live|go live|readiness score"
_APPROVAL_PATTERN = (
    r"approval|approved|certification|certified|compliant|go-live|go live|readiness score"
)
_ALLOWED_NEGATED_PATTERNS = (
    re.compile(rf"does not [^.\n]*(?:{_VERDICT_PATTERN})[^.\n]*[.\n]", re.IGNORECASE),
    re.compile(rf"did not [^.\n]*(?:{_VERDICT_PATTERN})[^.\n]*[.\n]", re.IGNORECASE),
    re.compile(rf"no [^.\n]*(?:{_APPROVAL_PATTERN})[^.\n]*[.\n]", re.IGNORECASE),
)


def _remove_allowed_negated_context(text: str) -> str:
    checked = text
    for pattern in _ALLOWED_NEGATED_PATTERNS:
        checked = pattern.sub(" ", checked)
    return checked


def find_forbidden_terms(text: str) -> list[str]:
    checked = _remove_allowed_negated_context(text).casefold()
    found: list[str] = []
    for phrase in FORBIDDEN_VERDICT_PHRASES:
        if phrase.casefold() in checked:
            found.append(phrase)
    return found


def assert_safe_generated_text(text: str, *, context: str) -> None:
    found = find_forbidden_terms(text)
    if found:
        terms = ", ".join(found)
        raise ValueError(f"Unsafe generated text for {context}: {terms}")
