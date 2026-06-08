# Data Migration Readiness Review Agent

Given a migration pack, what evidence do we have, what gaps or mismatches are visible, and what should a human reviewer check next?

## What this tool is

Data Migration Readiness Review Agent is a local command-line tool. It reads a local migration pack and writes deterministic review artifacts. It helps a human reviewer inspect migration evidence before that reviewer records decisions in the normal workplace process.

The tool prepares evidence and review material. It does not assess readiness, approve migration, decide go-live, certify compliance, certify security, certify privacy, certify legal status, certify governance status, replace human review, or make a final decision.

## The workplace problem

Migration reviews often involve source extracts, target extracts, mapping files, contracts, reconciliation notes, test results, risks, cutover notes, rollback notes, and acceptance notes.

Those files are often spread across folders. People may ask whether the migration can proceed before the evidence is organized. The tool helps structure that evidence so a reviewer can see what exists, what is missing, what mismatches were found, and what needs follow-up.

## What this project does

1. Reads the manifest.
2. Inventories referenced files.
3. Profiles CSV source and target files.
4. Inventories schemas.
5. Reviews mappings and contracts.
6. Runs deterministic reconciliation checks.
7. Flags sensitive-field indicators.
8. Reviews supplied test evidence structure.
9. Checks expected evidence coverage.
10. Builds `review_pack.json`.
11. Writes `reviewer_summary.md`.
12. Optionally writes bounded LLM reviewer notes.
13. Records trace metadata.

## What to open first

Open `reviewer_summary.md` first after a run. It gives the run boundary, summary counts, grouped findings, artifact index, and follow-up checklist.

Then open:

- `review_pack.json` for structured findings and follow-up items.
- `migration_readiness_trace.json` to see what ran and which artifacts were written.
- Detailed JSON artifacts for each review area.
- `llm_reviewer_notes.json` only as supplemental notes when optional LLM review was requested or skipped.

## Why deterministic evidence matters

The same inputs should produce the same review evidence. The workflow writes JSON artifacts before the Markdown summary so the summary is based on structured records. Optional LLM notes are downstream of the deterministic review pack and do not change deterministic findings.

## Why not just ask an LLM?

An LLM can sound confident without showing evidence. This tool builds deterministic artifacts first. Optional LLM notes use bounded `review_pack.json` context, are written separately, and do not change deterministic findings or authority boundaries.

## Quick start

Install the package with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the example pack with the Python module form:

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --output-dir outputs/example --no-llm
```

Or use the installed CLI form:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/example --no-llm
```

Committed sample outputs are available in `examples/example_outputs/` for a quick look without running the command.

## Optional LLM notes

Install the optional LLM dependency:

```bash
python -m pip install -e ".[dev,llm]"
```

Run with optional LLM reviewer notes:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/llm-example --llm-review --llm-model YOUR_MODEL_NAME
```

`OPENAI_API_KEY` is used by the OpenAI client. `OPENAI_MODEL` can be used as a default model if `--llm-model` is not supplied. Do not put real key values in commands, docs, committed files, or shared artifacts.

## Optional LangGraph orchestration

Install the optional graph dependency:

```bash
python -m pip install -e ".[dev,graph]"
```

Run the same workflow through the LangGraph orchestrator:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/langgraph-example --no-llm --orchestrator langgraph
```

`standard` is the default orchestrator. LangGraph changes orchestration only. It does not change artifact meaning or authority boundaries.

## Output artifacts

| Artifact | Purpose |
| --- | --- |
| `migration_inventory.json` | Lists manifest-declared files and file-presence gaps. |
| `dataset_profiles.json` | Profiles CSV headers, row counts, nulls, inferred types, and duplicate keys. |
| `schema_inventory.json` | Lists source and target schemas and key-column presence. |
| `mapping_review.json` | Reviews mapping files against source and target schemas. |
| `contract_review.json` | Reviews contract files against target schemas and profiles. |
| `reconciliation_results.json` | Records deterministic row-count, key-overlap, and mapped-field checks. |
| `sensitive_field_review.json` | Records sensitive-field indicators from hints and column-name patterns. |
| `test_evidence_review.json` | Reviews supplied test evidence structure. |
| `evidence_coverage_review.json` | Checks whether expected evidence types are declared and present. |
| `review_pack.json` | Aggregates deterministic findings and follow-up items. |
| `reviewer_summary.md` | Human-readable summary. Open this first. |
| `llm_reviewer_notes.json` | Optional supplemental LLM notes or skipped status. |
| `migration_readiness_trace.json` | Records run settings, summaries, artifact paths, and orchestration metadata. |

## Safety and authority boundaries

The tool may include:

- Column names.
- Aggregate counts.
- File paths.
- Schema names.
- Status values.
- Bounded key or mismatch samples in deterministic reconciliation artifacts.
- Human follow-up prompts.

The tool should not include:

- Full raw datasets.
- API keys.
- Approval decisions.
- Legal, privacy, compliance, security, or governance verdicts.
- Final migration decisions.

## Project structure

```text
src/data_migration_readiness_review_agent/  Python package and CLI workflow
docs/                                      Plain-English docs
examples/migration_pack/                   Small local example migration pack
examples/example_outputs/                  Committed example outputs
tests/                                     Unit and CLI tests
```

## Run tests

```bash
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

## Limitations and non-goals

- Local files only.
- CSV datasets only.
- CSV mappings only.
- YAML/YML contracts only.
- No PDF, DOCX, or OCR support.
- No database, cloud, or SaaS connectors.
- No transformation execution.
- No remediation.
- No final approval, no readiness score, and no go-live decision.

## Further reading

- [Architecture](docs/architecture.md)
- [Design principles](docs/design_principles.md)
- [Artifacts](docs/artifacts.md)
- [Demo workflow](docs/demo_workflow.md)
- [Example commands](docs/example_commands.md)
- [Migration pack format](docs/migration_pack_format.md)
- [Reviewer workflow](docs/reviewer_workflow.md)
- [Safety boundaries](docs/safety_boundaries.md)
- [LLM reviewer notes](docs/llm_reviewer_notes.md)
- [Orchestration](docs/orchestration.md)
- [Roadmap](docs/roadmap.md)
