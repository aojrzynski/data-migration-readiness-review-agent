# Orchestration

The workflow can be coordinated by the default `standard` orchestrator or by the optional `langgraph` orchestrator.

## Standard orchestrator

`standard` is the default. It runs the local deterministic stages and writes the artifact set.

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/example --no-llm
```

## LangGraph orchestrator

The `langgraph` orchestrator is optional. Install the graph extra first:

```bash
python -m pip install -e ".[dev,graph]"
```

Then run:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/langgraph-example --no-llm --orchestrator langgraph
```

## Artifact semantics

Both orchestration paths produce the same artifact semantics. LangGraph changes coordination only. It does not add review authority, change deterministic findings, or make optional LLM notes more authoritative.

## Trace metadata

`migration_readiness_trace.json` records the orchestration mode and artifact paths. Use the trace to confirm whether the run used `standard` or `langgraph`.

## External services

LangGraph orchestration does not require LangSmith or LangGraph Cloud for this local workflow.
