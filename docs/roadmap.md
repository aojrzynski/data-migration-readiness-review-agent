# Roadmap

This roadmap is cautious. It describes possible directions without changing the current authority boundary.

## Current v1 capability

The current tool can:

- Read a local manifest-based migration pack.
- Inventory declared files and missing references.
- Profile CSV source and target datasets.
- Build schema inventory from CSV headers.
- Review CSV mappings against observed schemas.
- Review YAML/YML contracts against target schemas and profiles.
- Run deterministic row-count, key-overlap, and direct mapped-field reconciliation checks.
- Record sensitive-field indicators.
- Review supplied test evidence structure.
- Check expected evidence coverage.
- Write `review_pack.json`, `reviewer_summary.md`, `llm_reviewer_notes.json`, and trace metadata.
- Run with the default standard orchestrator or optional LangGraph orchestration.

## Possible near-term improvements

- Support more dataset formats later, such as XLSX or Parquet.
- Larger-file safeguards.
- More explicit contract rules.
- Better reconciliation configuration.
- Richer test evidence parsing.
- Path-normalized committed examples.
- Documentation examples with intentional gaps and mismatches.

## Possible later extensions

- Optional connectors.
- Richer orchestration.
- More advanced LLM review notes.
- HTML report export.

## Non-goals

- No final approval.
- No readiness score.
- No legal, compliance, privacy, or security certification.
- No replacement for human review.
