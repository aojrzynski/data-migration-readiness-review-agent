# Overview

Data Migration Readiness Review Agent is a local command-line workflow for organizing migration review evidence. It accepts a migration pack directory, reads a manifest, validates referenced paths, runs deterministic checks, and writes a set of JSON and Markdown artifacts.

## Problem it is aimed at

Migration reviews often involve many files owned by different teams. Reviewers need to know what evidence was supplied, what was missing, what schemas and mappings look like, where reconciliation differences appear, and what follow-up questions remain. Without a repeatable local workflow, each reviewer may need to rebuild that picture manually.

This project helps by producing a consistent evidence pack from local files. It is intended to reduce manual sorting and make gaps easier to find.

## Current deterministic workflow

The CLI currently performs these local steps:

1. Load `manifest.yaml`, `manifest.yml`, or an explicit `--manifest` path.
2. Reject manifest and referenced paths that escape the migration pack directory.
3. Inventory declared migration files and missing references.
4. Profile source and target CSV datasets.
5. Build a schema inventory from observed CSV headers.
6. Review mapping CSV files against source and target schemas.
7. Review YAML/YML contracts against target schemas and dataset profiles.
8. Run deterministic reconciliation checks for row counts, key overlap, and direct mapped-field comparisons.
9. Record sensitive-field indicators based on column names and manifest hints.
10. Review supplied test-evidence file structure.
11. Check expected evidence-type coverage.
12. Aggregate findings into `review_pack.json`.
13. Write `reviewer_summary.md` for human review.
14. Write `llm_reviewer_notes.json` with default not-requested status, or optional supplemental notes when explicitly requested.
15. Write `migration_readiness_trace.json` with run settings and artifact summaries.

## How the artifacts fit together

The lower-level artifacts keep focused details: inventory, dataset profiles, schema inventory, mapping review, contract review, reconciliation results, sensitive-field review, test-evidence review, and evidence-coverage review.

`review_pack.json` is the compact machine-readable aggregation. It points back to source artifacts and groups findings for downstream tools or human triage.

`reviewer_summary.md` is the best first artifact for a person to open. It summarizes counts, groups findings, lists follow-up checklist items, and names the detailed artifacts to inspect next.

`llm_reviewer_notes.json` is reviewed after deterministic artifacts when optional notes are requested; it is supplemental only.

`migration_readiness_trace.json` records the run configuration and artifact summaries so reviewers can see how the artifacts were produced.

## Human review remains the authority

The workflow prepares evidence and deterministic findings. It does not approve migration activity, decide go-live, certify compliance, certify legal or privacy status, or replace human reviewers. Human teams must interpret the artifacts, inspect source evidence, document decisions, and apply organization-specific controls outside the tool.

## Optional LLM and orchestration later

Optional LLM reviewer notes can be requested explicitly. They remain bounded, traceable, and non-authoritative. Deterministic local artifacts remain the evidence base, and human reviewers remain responsible for decisions. LangGraph orchestration is not part of this workflow.
