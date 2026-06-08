# Architecture

The workflow reads a local migration pack and writes a set of review artifacts. Each stage has a narrow job so a reviewer can inspect one part of the evidence without mixing it with every other concern.

## Why stages are separate

Separate stages make the evidence easier to check:

- Inventory answers: which files did the manifest declare, and are they present?
- Dataset profiling answers: what do the CSV files look like at a basic structural level?
- Schema inventory answers: which source and target columns were observed?
- Mapping and contract review answer: do declared files line up with observed schemas?
- Reconciliation answers: where do deterministic row-count, key, or direct mapped-field checks show differences?
- Sensitive-field review answers: which columns look like they may need handling review?
- Test evidence and coverage review answer: what supporting evidence was declared and present?
- Review pack and summary make those details easier to inspect.
- Trace records what ran.

## Flow

```text
migration pack
-> manifest
-> inventory
-> dataset profiles
-> schema inventory
-> mapping review
-> contract review
-> reconciliation results
-> sensitive-field review
-> test evidence review
-> evidence coverage review
-> review pack
-> reviewer summary
-> optional LLM reviewer notes
-> trace
```

## Orchestrators

The `standard` orchestrator is the default. It runs the local deterministic workflow in the expected order.

The optional `langgraph` orchestrator can run the same artifact workflow when the graph extra is installed. LangGraph changes coordination only. It does not change artifact meaning, add review authority, or make LLM notes part of the deterministic evidence base.

## Artifact chain

Detailed artifacts are written first. `review_pack.json` aggregates deterministic findings and follow-up items. `reviewer_summary.md` is written from those records for human reading. `llm_reviewer_notes.json` is optional and supplemental. `migration_readiness_trace.json` records settings, artifact paths, summaries, and orchestration metadata.

Deterministic artifacts remain authoritative for the tool output. Human reviewers remain responsible for interpretation and decisions outside the tool.
