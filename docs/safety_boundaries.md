# Safety boundaries

This page repeats the safety and authority boundaries for generated artifacts, documentation, and optional LLM reviewer notes.

## What the tool may include

The tool may include:

- Column names.
- Aggregate counts.
- File paths.
- Schema names.
- Status values.
- Bounded key or mismatch samples in deterministic reconciliation artifacts.
- Human follow-up prompts.

## What the tool should not include

The tool should not include:

- Full raw datasets.
- API keys.
- Raw secrets.
- Legal, privacy, compliance, security, or governance verdicts.
- Final migration decisions.

## Raw data and preview policy

The tool is designed to write summaries rather than full raw datasets. Raw rows should not be copied into documentation or optional LLM prompts. Some deterministic artifacts may include bounded samples, such as mismatch samples, to help a reviewer locate evidence to inspect.

## Sensitive-field indicator boundary

Sensitive-field indicators are based on manifest hints and column-name patterns. They are prompts for human review. They are not legal, privacy, compliance, security, or governance classifications.

## Optional LLM input boundary

Optional LLM notes use bounded `review_pack.json` context. LLM context should not include raw rows or raw sensitive values. Do not put API keys or secrets in prompts, manifests, evidence files, or committed artifacts.

## Safe-language boundary

Use evidence language: found, missing, mismatched, skipped, needs review, and follow up. The tool does not assess readiness, approve migration, decide go-live, certify compliance, certify security, certify privacy, certify legal status, certify governance status, or make a final decision.

## Authority boundary

The tool prepares review material. Human reviewers and the organization review process remain responsible for interpretation, decisions, and any required controls outside the tool.
