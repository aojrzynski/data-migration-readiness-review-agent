# Data Migration Readiness Review Agent

Data migration reviews often require people to inspect many small pieces of evidence: source extracts, target extracts, mappings, contract files, reconciliation notes, test evidence, risk notes, cutover notes, rollback notes, and acceptance notes. Those files can be spread across folders and can be hard to evaluate consistently.

Data Migration Readiness Review Agent is a local Python CLI that turns a migration pack into deterministic review artifacts. It inventories supplied files, profiles CSV datasets, checks declared mappings and contracts against observed schemas, performs deterministic reconciliation checks, records sensitive-field indicators, reviews supplied test-evidence structure, checks evidence coverage, and writes a reviewer-facing summary.

The tool prepares evidence for human review. It does not assess readiness, approve migration activity, decide go-live, certify compliance, certify security or privacy status, certify legal or governance status, or replace human reviewers.

## Approach

- **Local-first:** the CLI reads local files and writes local artifacts. It does not make cloud calls.
- **Deterministic-first:** current checks use the Python standard library plus PyYAML and are intended to produce repeatable artifacts from the same pack.
- **Artifact-driven:** each review step writes a small JSON or Markdown artifact that can be opened directly.
- **Human authority:** the artifacts organize evidence and findings; people remain responsible for decisions outside the tool.
- **Bounded output:** previews and samples are limited so generated files stay small and do not dump full datasets.

## Quick start

From the repository root, run the example migration pack:

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --output-dir outputs/example --no-llm
```

After package installation, the installed CLI form is:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/example --no-llm
```

Open `outputs/example/reviewer_summary.md` first. It is the best first artifact to open for a human reviewer because it gives the run boundary, summary counts, grouped findings, artifact index, and follow-up checklist.

Committed sample artifacts are available in `examples/example_outputs/` for a quick look without running the command.

## Current artifact list

- `migration_inventory.json` inventories manifest metadata, declared references, file presence, and missing-file gaps.
- `dataset_profiles.json` profiles source and target CSV files with row counts, columns, nulls, inferred types, distinct counts, duplicate-key counts, and bounded previews.
- `schema_inventory.json` summarizes source and target schema overlap and key-column presence.
- `mapping_review.json` checks mapping CSV rows against observed source and target schemas.
- `contract_review.json` checks YAML/YML contract fields against target schemas and dataset profiles.
- `reconciliation_results.json` compares row counts, key overlap, and direct mapped-field values.
- `sensitive_field_review.json` records deterministic sensitive-field indicators without writing raw sensitive values.
- `test_evidence_review.json` records supplied test-evidence structure, status counts, and bounded failed/warning summaries.
- `evidence_coverage_review.json` records whether expected evidence types are declared and present.
- `review_pack.json` aggregates deterministic findings and follow-up checklist items in compact machine-readable form.
- `reviewer_summary.md` presents the reviewer-facing summary and checklist.
- `migration_readiness_trace.json` records run settings and artifact summaries.

## Documentation

- [Overview](docs/overview.md)
- [Local usage](docs/local_usage.md)
- [Migration pack format](docs/migration_pack_format.md)
- [Artifacts](docs/artifacts.md)
- [Reviewer workflow](docs/reviewer_workflow.md)
- [Design principles](docs/design_principles.md)

## Current limitations

- CSV is the only dataset format profiled.
- Mapping files are CSV only.
- Contract files are YAML/YML only.
- Test evidence is structurally reviewed; document quality and business meaning are not evaluated.
- Evidence files are treated mainly as declared presence evidence.
- Reconciliation checks are deterministic and limited to configured keys and direct mapped fields.
- Outputs are review aids, not verdicts.

## What the tool does not do

The current workflow does not add readiness scoring, readiness dimension assessment, final go/no-go recommendations, LLM review, LangGraph orchestration, cloud connectors, approval workflows, remediation generation, legal/compliance/privacy certification, or automatic decisions.
