from __future__ import annotations

import json
from typing import Any

MAX_FINDINGS_SENT = 50
MAX_FOLLOW_UP_ITEMS_SENT = 50

LLM_REVIEW_INSTRUCTIONS = """
You are producing supplemental reviewer notes only.
The deterministic artifacts are authoritative.
Do not approve the migration.
Do not decide go-live.
Do not certify compliance, security, privacy, legal, or governance status.
Do not say the migration is ready.
Do not create a readiness score.
Do not override deterministic findings.
Do not invent evidence not present in the review pack.
Only suggest human follow-up questions and areas to inspect.
Return strict JSON only.

Return JSON with this exact top-level shape:
{
  "summary": "Brief supplemental summary for a human reviewer.",
  "observations": [
    {
      "category": "reconciliation",
      "message": "Observation grounded in the deterministic review pack.",
      "source_finding_ids": ["..."]
    }
  ],
  "suggested_human_questions": [
    {
      "category": "mapping",
      "question": "Question for a human reviewer.",
      "source_finding_ids": ["..."]
    }
  ],
  "caveats": [
    "Short caveat about the limits of the LLM notes."
  ]
}
""".strip()


def build_llm_context(
    review_pack: dict[str, Any], *, max_input_chars: int
) -> tuple[str, dict[str, Any]]:
    """Build bounded LLM context from the in-memory review pack only."""
    bounded_context = {
        "boundary_instructions": [
            "Produce supplemental reviewer notes only.",
            "Deterministic artifacts remain authoritative.",
            "Suggest human follow-up questions and areas to inspect only.",
        ],
        "migration": review_pack.get("migration", {}),
        "source_artifacts": review_pack.get("source_artifacts", []),
        "summary": review_pack.get("summary", {}),
        "sections": review_pack.get("sections", []),
        "findings": review_pack.get("findings", [])[:MAX_FINDINGS_SENT],
        "follow_up_checklist": review_pack.get("follow_up_checklist", [])[
            :MAX_FOLLOW_UP_ITEMS_SENT
        ],
    }
    original_context = json.dumps(bounded_context, indent=2, sort_keys=True)
    sent_context = original_context[:max_input_chars]
    input_truncated = len(sent_context) < len(original_context)
    input_policy = {
        "source": "review_pack",
        "raw_data_rows_included": False,
        "raw_sensitive_values_included": False,
        "max_input_chars": max_input_chars,
        "original_context_char_count": len(original_context),
        "sent_context_char_count": len(sent_context),
        "input_truncated": input_truncated,
        "max_findings_sent": MAX_FINDINGS_SENT,
        "max_follow_up_items_sent": MAX_FOLLOW_UP_ITEMS_SENT,
    }
    return sent_context, input_policy
