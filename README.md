# Data Migration Readiness Review Agent

Data migrations usually need many people to check the same evidence: source extracts, target extracts, mappings, business rules, contract files, test results, risks, cutover notes, rollback notes, and acceptance evidence.

This project is a local-first Python CLI workflow for preparing that evidence into a migration readiness review pack. The goal is to help reviewers see what evidence was supplied, what checks were run, what gaps were found, and what still needs human review.

The tool reviews migration readiness evidence. It does not approve a migration, decide go-live, certify compliance, certify security or privacy status, certify legal or governance status, or replace human reviewers.

## Core principles

- Local-first: inputs and outputs stay on the local machine unless the user chooses otherwise outside this tool.
- Artifact-driven: review output should be based on explicit supplied files and generated artifacts.
- Deterministic evidence first: repeatable checks come before any language-model assistance.
- LLM later, bounded and validated: PR #1 has no LLM dependency and makes no external LLM calls.
- Human authority remains final: the tool prepares review material, but people make decisions.
- No cloud services and no hidden external calls.
- No approval or go-live verdict language.

## What this tool will eventually do

Later versions are expected to help prepare a review pack from supplied migration materials, including:

- source and target extracts
- mapping files
- contract and rule files
- migration test results
- reconciliation evidence
- known risks and open questions
- cutover and rollback notes
- acceptance evidence

The intended workflow is to produce clear local artifacts that a human reviewer can inspect.

## What PR #1 currently does

PR #1 only creates the repository scaffold and a minimal CLI.

The CLI can:

- accept a local migration pack directory with `--pack`
- create an output directory with `--output-dir`
- record whether `--no-llm` was used
- record the selected `--orchestrator standard` value
- write a simple `migration_readiness_trace.json` artifact

PR #1 does not parse the manifest, profile datasets, review mappings, review contracts, reconcile records, detect sensitive fields, call an LLM, run LangGraph orchestration, or perform a readiness assessment.

## Run the PR #1 scaffold CLI

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
outputs/example/migration_readiness_trace.json
```

That file is only a scaffold trace. It is not an assessment result or approval.

## Example migration pack skeleton

The repository includes a placeholder pack at `examples/migration_pack/`:

```text
examples/migration_pack/
├── manifest.yaml
├── contracts/
├── data/
├── evidence/
├── mappings/
└── tests/
```

The manifest is present only as a placeholder in PR #1. The CLI does not read or validate it yet.

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
- Future PR: manifest loading and validation
- Future PR: deterministic dataset and mapping evidence checks
- Future PR: contract and rule review checks
- Future PR: reconciliation and test-result summaries
- Future PR: sensitive-field evidence checks
- Future PR: bounded LLM review over validated artifacts
- Future PR: orchestration once the deterministic steps are established

## License

MIT.
