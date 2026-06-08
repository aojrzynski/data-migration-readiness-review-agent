# Demo workflow

This demo uses the small example migration pack in the repository. It shows how a reviewer can move from generated artifacts to human follow-up work.

## 1. Run the example command

Installed CLI form:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/example --no-llm
```

Python module form:

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --output-dir outputs/example --no-llm
```

## 2. Open `reviewer_summary.md`

Start with `outputs/example/reviewer_summary.md`. It is the first file to open because it gives the run boundary, summary counts, grouped findings, artifact index, and follow-up checklist.

## 3. Read summary counts

Use the counts to understand the size of the supplied pack and the number of generated findings. Counts are signals for review, not conclusions.

## 4. Review the follow-up checklist

Work through the checklist as human review prompts. Assign owners, ask evidence questions, and record follow-up outside the tool.

## 5. Open `review_pack.json`

Use `outputs/example/review_pack.json` when you need structured finding details or want to copy finding records into another review process.

## 6. Open detailed artifacts as needed

Use the artifact index to inspect detailed files such as `mapping_review.json`, `contract_review.json`, `reconciliation_results.json`, `sensitive_field_review.json`, `test_evidence_review.json`, and `evidence_coverage_review.json`.

## 7. Check the trace

Open `outputs/example/migration_readiness_trace.json` to see the run settings, artifact paths, summary counts, and orchestration mode.

## 8. Record human decisions outside the tool

Use the organization review process, ticketing system, change record, risk log, or meeting notes. A clean demo run does not remove the need for human review.
