# Artifacts

Open `reviewer_summary.md` first after a run. It is the human-readable entry point for the run boundary, summary counts, grouped findings, artifact index, and follow-up checklist.

The detailed JSON artifacts are written before the summary. `review_pack.json` aggregates deterministic findings and follow-up items. `llm_reviewer_notes.json` is optional and supplemental. `migration_readiness_trace.json` records what ran.

Common exclusions apply across artifacts: outputs should not contain full raw datasets, API keys, raw secrets, legal/privacy/compliance/security/governance verdicts, or final migration decisions.

## `migration_inventory.json`

### Purpose

Lists manifest-declared files and file-presence gaps.

### When written

Written after the manifest is loaded and paths are checked.

### Open it for

Use it to see migration metadata, declared datasets, mappings, contracts, test results, evidence files, and missing references.

### What it contains

Manifest metadata, pack path metadata, referenced files, file existence status, file sizes, counts, sensitive-field hints, expected dimensions, and inventory notes.

### What it excludes

It does not parse full dataset contents or judge evidence quality.

### Artifact type

Deterministic JSON.

### Authority boundary

It records declared file presence. It does not assess readiness or make a migration decision.

## `dataset_profiles.json`

### Purpose

Profiles CSV headers, row counts, nulls, inferred types, distinct counts, and duplicate keys.

### When written

Written after inventory, using declared source and target CSV paths.

### Open it for

Use it to understand basic CSV structure and simple data-shape signals.

### What it contains

Per-dataset source and target profiles, columns, row counts, null counts, inferred type summaries, distinct counts, duplicate key counts, and bounded previews.

### What it excludes

It does not write full raw datasets, cleanse data, or execute transformations.

### Artifact type

Deterministic JSON.

### Authority boundary

It gives structural evidence for review. It does not decide whether data quality is acceptable.

## `schema_inventory.json`

### Purpose

Lists source and target schemas and key-column presence.

### When written

Written after dataset profiles are available.

### Open it for

Use it to compare observed source and target columns and check whether declared keys are present.

### What it contains

Observed source columns, observed target columns, shared columns, source-only columns, target-only columns, and key-column checks.

### What it excludes

It does not design schemas or validate business data models.

### Artifact type

Deterministic JSON.

### Authority boundary

It records observed schema evidence. It does not certify schema design.

## `mapping_review.json`

### Purpose

Reviews mapping files against source and target schemas.

### When written

Written after schema inventory is available.

### Open it for

Use it to find mapping rows that reference missing source or target columns and target columns without declared mappings.

### What it contains

Per-mapping review records, row-level findings, missing source references, missing target references, unmapped target columns, and summary counts.

### What it excludes

It does not execute mappings or prove transformation correctness.

### Artifact type

Deterministic JSON.

### Authority boundary

It records mapping alignment evidence. It does not approve migration or make business-rule decisions.

## `contract_review.json`

### Purpose

Reviews contract files against target schemas and profiles.

### When written

Written after dataset profiles and schema inventory are available.

### Open it for

Use it to inspect contract fields that are missing from target data, required-field null warnings, and simple type warnings.

### What it contains

Per-contract review records, parsed fields, missing required target fields, null warnings, type warnings, and summary counts.

### What it excludes

It does not provide legal, privacy, compliance, security, or governance verdicts.

### Artifact type

Deterministic JSON.

### Authority boundary

It records contract-to-data alignment evidence. It does not certify compliance or contract meaning.

## `reconciliation_results.json`

### Purpose

Records deterministic row-count, key-overlap, and mapped-field checks.

### When written

Written after profiles, schema inventory, and mapping review are available.

### Open it for

Use it to inspect row-count differences, missing source keys in target, unexpected target keys, direct mapped-field mismatches, skipped checks, and samples.

### What it contains

Dataset-level reconciliation records, row-count checks, key-overlap checks, field-comparison checks, bounded key samples, bounded mismatch samples, and summary counts.

### What it excludes

It does not compare unsupported transformations, write full raw datasets, or replace human reconciliation review.

### Artifact type

Deterministic JSON.

### Authority boundary

It records deterministic comparison evidence. It does not decide go-live or make a final migration decision.

## `sensitive_field_review.json`

### Purpose

Records sensitive-field indicators from manifest hints and column-name patterns.

### When written

Written after schema inventory and dataset profiles are available.

### Open it for

Use it to see which columns may need handling review by the right owner.

### What it contains

Flagged source and target columns, indicator types, matching hints or patterns, dataset summaries, and review-scope notes.

### What it excludes

It does not write raw sensitive values and does not classify legal or privacy status.

### Artifact type

Deterministic JSON.

### Authority boundary

Indicators are prompts for human review. They are not legal, privacy, compliance, security, or governance classifications.

## `test_evidence_review.json`

### Purpose

Reviews supplied test evidence structure.

### When written

Written after sensitive-field review in the default artifact chain.

### Open it for

Use it to see which test result files were declared, whether CSV structure could be read, and what status counts were found.

### What it contains

Test result records, file presence, CSV headers, row counts, status counts, bounded failed or warning summaries, and summary counts.

### What it excludes

It does not judge test design quality or business meaning.

### Artifact type

Deterministic JSON.

### Authority boundary

It records supplied test-evidence structure. It does not make a testing decision.

## `evidence_coverage_review.json`

### Purpose

Checks whether expected evidence types are declared and present.

### When written

Written after test evidence review.

### Open it for

Use it to compare expected review dimensions with declared evidence and file-presence status.

### What it contains

Expected evidence dimensions, declared evidence types, present evidence types, missing expected evidence, and summary counts.

### What it excludes

It does not read every evidence file deeply or judge evidence sufficiency.

### Artifact type

Deterministic JSON.

### Authority boundary

It records coverage signals for follow-up. It does not assess readiness.

## `review_pack.json`

### Purpose

Aggregates deterministic findings and follow-up items.

### When written

Written after all detailed deterministic review artifacts are available.

### Open it for

Use it for structured finding details, downstream triage, or copying findings into a separate review process.

### What it contains

Run and migration metadata, artifact references, grouped findings, summary counts, follow-up checklist items, and deterministic notes.

### What it excludes

It does not include full raw datasets or optional LLM text as the evidence base.

### Artifact type

Deterministic JSON aggregation.

### Authority boundary

It is the structured review pack. It does not approve migration or make a final decision.

## `reviewer_summary.md`

### Purpose

Human-readable summary. Open this first.

### When written

Written after `review_pack.json` is available.

### Open it for

Use it as the first review page for run scope, summary counts, grouped findings, artifact index, and follow-up checklist.

### What it contains

Plain-language summary sections generated from deterministic records.

### What it excludes

It does not include full raw datasets, final decisions, or optional LLM authority.

### Artifact type

Deterministic Markdown summary.

### Authority boundary

It is a review aid. It does not assess readiness, decide go-live, or replace human review.

## `llm_reviewer_notes.json`

### Purpose

Records optional supplemental LLM notes or skipped status.

### When written

Written after `review_pack.json` and `reviewer_summary.md`. It is also written in no-LLM runs with a not-requested status.

### Open it for

Use it only as supplemental notes after reviewing deterministic artifacts.

### What it contains

LLM review status, optional model metadata, bounded note sections when completed, failure or skip reasons when applicable, and validation status.

### What it excludes

It should not contain full raw datasets, raw sensitive values, API keys, or secrets.

### Artifact type

JSON status and optional supplemental notes.

### Authority boundary

LLM notes are non-authoritative. They do not change deterministic findings or make decisions.

## `migration_readiness_trace.json`

### Purpose

Records run settings, summaries, artifact paths, and orchestration metadata.

### When written

Written at the end of the workflow after other artifacts are written.

### Open it for

Use it to confirm pack path, manifest path, output directory, LLM settings, orchestration mode, artifact paths, and summary metadata.

### What it contains

Run configuration, artifact paths, artifact summaries, package version, manifest path, output path, LLM note status, and orchestration metadata.

### What it excludes

It does not contain raw datasets or hidden environment secret values.

### Artifact type

Deterministic JSON trace with local run metadata.

### Authority boundary

It records how the run was produced. It does not make review decisions.
