# Example commands

These commands are intended to be copied from the repository root.

## Install base development dependencies

```bash
python -m pip install -e ".[dev]"
```

## Help and version

```bash
data-migration-readiness-review --help
```

```bash
data-migration-readiness-review --version
```

## Default standard no-LLM run

The `standard` orchestrator is the default.

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/example --no-llm
```

## Python module no-LLM run

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --output-dir outputs/example --no-llm
```

## Custom output directory

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/customer-review --no-llm
```

## Explicit manifest

```bash
data-migration-readiness-review --pack examples/migration_pack --manifest manifest.yaml --output-dir outputs/example --no-llm
```

## Optional LLM notes run

Requires the optional LLM extra:

```bash
python -m pip install -e ".[dev,llm]"
```

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/llm-example --llm-review --llm-model YOUR_MODEL_NAME
```

You can limit the serialized review-pack context sent to the optional LLM:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/llm-example --llm-review --llm-model YOUR_MODEL_NAME --llm-max-input-chars 12000
```

## Optional LangGraph run

Requires the optional graph extra:

```bash
python -m pip install -e ".[dev,graph]"
```

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/langgraph-example --no-llm --orchestrator langgraph
```

## Optional LLM plus LangGraph run

Requires both optional extras:

```bash
python -m pip install -e ".[dev,llm,graph]"
```

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/llm-langgraph-example --llm-review --llm-model YOUR_MODEL_NAME --orchestrator langgraph
```

## PowerShell environment variable notes

Set environment variables for the current PowerShell session without showing real key values in shared docs:

```powershell
$env:OPENAI_API_KEY = "set-your-key-outside-shared-files"
$env:OPENAI_MODEL = "YOUR_MODEL_NAME"
```

Then run:

```powershell
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/llm-example --llm-review
```

The OpenAI client uses `OPENAI_API_KEY`. `OPENAI_MODEL` is used as a default when `--llm-model` is not supplied.
