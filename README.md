# Data Migration Readiness Review Agent

Data migrations usually need many people to check the same evidence: source extracts, target extracts, mappings, business rules, contract files, test results, risks, cutover notes, rollback notes, and acceptance evidence.

This project is a local-first Python CLI workflow for preparing that evidence into a migration readiness review pack. The goal is to help reviewers see what evidence was supplied, what checks were run, what gaps were found, and what still needs human review.

The tool reviews migration readiness evidence. It does not approve a migration, decide go-live, certify compliance, certify security or privacy status, certify legal or governance status, or replace human reviewers.

## Core principles

- Local-first: inputs and outputs stay on the local machine unless the user chooses otherwise outside this tool.
- Artifact-driven: review output should be based on explicit supplied files and generated artifacts.
- Deterministic evidence first: repeatable checks come before any language-model assistance.
- LLM later, bounded and validated: PR #3 has no LLM dependency and makes no external LLM calls.
- Human authority remains final: the tool prepares review material, but people make decisions.
- No cloud services and no hidden external calls.
- No approval or go-live verdict language.

## What PR #3 currently does

PR #3 adds deterministic CSV dataset profiling and schema inventory on top of local manifest intake and migration pack inventory.

The CLI can:

- accept a local migration pack directory with `--pack`
- discover `manifest.yaml`, or `manifest.yml` when `manifest.yaml` is not present
- accept an explicit manifest with `--manifest PATH`
- validate the manifest's basic shape
- verify that the manifest and referenced files resolve inside the pack directory
- inventory files referenced by the manifest
- record missing referenced files as `gap_found` entries without crashing the run
- create an output directory with `--output-dir`
- record whether `--no-llm` was used
- record the selected `--orchestrator standard` value
- profile source and target CSV datasets referenced by the manifest
- capture row counts, column order, null counts, null rates, inferred types, bounded previews, distinct counts, and duplicate key counts within each file
- write `migration_inventory.json`
- write `dataset_profiles.json`
- write `schema_inventory.json`
- write an enriched `migration_readiness_trace.json`

PR #3 does not compare source and target records, validate mappings, review contracts, run reconciliation, detect sensitive fields, analyze test evidence, call an LLM, run LangGraph orchestration, or perform a readiness assessment.

## Run the PR #3 profiling CLI

From the repository root:

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --output-dir outputs/example --no-llm
```

After package installation, the intended CLI command is:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/example --no-llm
```

After running either command, open:

```text
outputs/example/migration_inventory.json
outputs/example/dataset_profiles.json
outputs/example/schema_inventory.json
outputs/example/migration_readiness_trace.json
```

`migration_inventory.json` contains manifest metadata, dataset declarations, referenced file metadata, counts, and any missing-file gaps. `dataset_profiles.json` contains CSV header details, row counts, column statistics, duplicate key counts, and bounded previews. `schema_inventory.json` lists source and target columns, key column presence, and schema overlap. `migration_readiness_trace.json` records the local run settings, manifest path, artifacts written, inventory counts, dataset profiling summary, and schema inventory summary.

These files are profiling and inventory artifacts only. They are not assessment results or approval artifacts.

## Manifest behavior

By default, the CLI looks for a manifest in the migration pack directory:

1. `manifest.yaml`
2. `manifest.yml`

If neither file exists, the CLI exits non-zero with a clear error. You can override discovery with:

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --manifest manifest.yaml --output-dir outputs/example --no-llm
```

Relative `--manifest` values are resolved relative to the pack directory. Manifest paths and all referenced file paths must resolve inside the pack directory, including after symlink resolution.

## Example migration pack

The repository includes a tiny sample pack at `examples/migration_pack/`:

```text
examples/migration_pack/
├── manifest.yaml
├── contracts/
│   ├── account_contract.yaml
│   └── customer_contract.yaml
├── data/
│   ├── source_accounts.csv
│   ├── source_customers.csv
│   ├── target_accounts.csv
│   └── target_customers.csv
├── evidence/
│   ├── acceptance_notes.md
│   ├── cutover_plan.md
│   ├── migration_notes.md
│   ├── risk_log.md
│   └── rollback_plan.md
├── mappings/
│   ├── account_mapping.csv
│   └── customer_mapping.csv
└── tests/
    ├── reconciliation_summary.csv
    └── test_results.csv
```

The sample files are intentionally small. PR #3 profiles the CSV files in `data/` and inventories their schemas while keeping mappings, contracts, tests, and evidence as tiny placeholders that are not parsed yet.

## Development

Install the package with development tools:

```bash
python -m pip install -e ".[dev]"
```

Run local checks:

```bash
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

## Current roadmap

- PR #1: repository scaffold, project framing, minimal CLI trace artifact
- PR #2: manifest loading, validation, migration pack inventory, enriched trace artifact
- PR #3: deterministic CSV dataset profiling and schema inventory artifacts
- Future PR: deterministic mapping evidence checks
- Future PR: contract and rule review checks
- Future PR: reconciliation and test-result summaries
- Future PR: sensitive-field evidence checks
- Future PR: bounded LLM review over validated artifacts
- Future PR: orchestration once the deterministic steps are established

## License

MIT.
