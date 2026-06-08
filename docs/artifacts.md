# Artifacts

The CLI writes focused JSON artifacts plus a human-readable reviewer summary. Each artifact is deterministic for the same input pack, except trace paths may reflect the local filesystem.

## `migration_inventory.json`

- **Purpose:** Records migration metadata, declared datasets, mappings, contracts, test results, evidence, referenced file presence, and missing-file gaps.
- **Main sections:** `migration`, `pack`, `datasets`, `referenced_files`, `gaps`, `counts`, `notes`.
- **Important statuses:** `inventory_created`; gap entries use `gap_found` when references are missing.
- **What it does not mean:** It does not judge the quality of supplied files or decide whether the migration can proceed.

## `dataset_profiles.json`

- **Purpose:** Profiles source and target CSV datasets with deterministic standard-library parsing.
- **Main sections:** `datasets`, per-file `source` and `target` profiles, column statistics, duplicate key counts, bounded previews, `notes`.
- **Important statuses:** `profile_created` for profiled files; gap statuses for missing or unreadable inputs.
- **What it does not mean:** It does not perform data cleansing, transformation, or full data-quality assessment.

## `schema_inventory.json`

- **Purpose:** Summarizes observed source and target columns, key-column presence, and schema overlap.
- **Main sections:** `datasets`, source and target columns, shared and side-specific columns, key-column checks.
- **Important statuses:** `schema_inventory_created`; dataset-level statuses reflect whether schema details were available.
- **What it does not mean:** It does not certify schema design or target model suitability.

## `mapping_review.json`

- **Purpose:** Reviews mapping CSV rows against observed source and target schemas.
- **Main sections:** `mapping_reviews`, row findings, missing source references, missing target references, unmapped target columns, `summary`.
- **Important statuses:** `mapping_review_created`; row findings may record missing or skipped mapping details.
- **What it does not mean:** It does not prove business transformation correctness or execute mappings.

## `contract_review.json`

- **Purpose:** Reviews YAML/YML contract fields against target schemas and dataset profiles.
- **Main sections:** `contract_reviews`, field findings, missing required target fields, null warnings, type mismatch warnings, `summary`.
- **Important statuses:** `contract_review_created`; finding statuses identify missing fields or warning conditions.
- **What it does not mean:** It does not certify legal, compliance, or data-governance obligations.

## `reconciliation_results.json`

- **Purpose:** Runs deterministic row-count, key-overlap, and direct mapped-field comparison checks.
- **Main sections:** `datasets`, row-count checks, key-overlap checks, field-comparison results, bounded samples, `summary`.
- **Important statuses:** `reconciliation_created`; dataset checks may record pass, warning, skipped, or gap-style statuses.
- **What it does not mean:** It does not decide go-live, validate transformations outside direct mapped fields, or replace human reconciliation review.

## `sensitive_field_review.json`

- **Purpose:** Records sensitive-field indicators based on manifest hints and deterministic column-name patterns.
- **Main sections:** `datasets`, flagged source and target columns, indicator sources, `summary`, `review_scope`.
- **Important statuses:** `sensitive_field_review_created`; indicators are findings for human review.
- **What it does not mean:** It does not classify legal/privacy status, decide handling acceptability, or write raw sensitive values.

## `test_evidence_review.json`

- **Purpose:** Reviews the structure of supplied test-evidence files.
- **Main sections:** `test_results`, CSV header and row summaries, status counts, bounded failed/warning summaries, `summary`.
- **Important statuses:** `test_evidence_review_created`; file-level statuses distinguish structured CSV review from metadata-only evidence or gaps.
- **What it does not mean:** It does not judge test design quality, coverage sufficiency, or business sign-off.

## `evidence_coverage_review.json`

- **Purpose:** Checks whether expected evidence types are declared and whether referenced files are present.
- **Main sections:** `expected_evidence_types`, `evidence_type_reviews`, `extra_evidence_types`, `summary`.
- **Important statuses:** `evidence_coverage_review_created`; missing evidence types or files are recorded as gaps.
- **What it does not mean:** It does not evaluate document content quality.

## `review_pack.json`

- **Purpose:** Provides the compact machine-readable aggregation of deterministic findings and follow-up checklist items.
- **Main sections:** `migration`, `sections`, `findings`, `follow_up_checklist`, `summary`, `source_artifacts`, `notes`.
- **Important statuses:** `review_pack_created`; findings are grouped by review area and severity-like labels for triage.
- **What it does not mean:** It does not score readiness or provide an automatic decision.

## `reviewer_summary.md`

- **Purpose:** Provides the best first artifact for a human reviewer.
- **Main sections:** scope boundary, summary counts, grouped findings, follow-up checklist, artifact index.
- **Important statuses:** This Markdown file does not have a JSON status; its content is generated only after `review_pack.json` is built.
- **What it does not mean:** It does not approve migration activity, decide go-live, certify compliance, or replace human reviewers.

## `migration_readiness_trace.json`

- **Purpose:** Records run settings and artifact summaries.
- **Main sections:** tool and version details, pack path, manifest path, output directory, `no_llm`, orchestrator mode, artifacts written, artifact summary counts, notes.
- **Important statuses:** `review_summary_artifacts_created`.
- **What it does not mean:** It does not prove that artifacts were reviewed by a human or that downstream decisions were made.
