# Local usage

## Requirements

- Python 3.11 or later
- Git
- A shell such as Git Bash, bash, or Windows PowerShell

## Clone the repository

```bash
git clone https://github.com/aojrzynski/data-migration-readiness-review-agent.git
cd data-migration-readiness-review-agent
```

## Create and activate a virtual environment

Git Bash or bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Install the package for development

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run tests and checks

```bash
python -m pytest -q
python -m ruff check .
```

## Run the example migration pack

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --output-dir outputs/example --no-llm
```

After package installation, this installed CLI form is equivalent:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/example --no-llm
```

## Orchestrator option

`--orchestrator standard` is currently the only supported orchestrator. It is the default, so the option can be omitted for normal local runs.

## Open the reviewer summary first

Open this file first after the example run:

```text
outputs/example/reviewer_summary.md
```

It is the best first artifact for a human reviewer because it summarizes counts, findings, the follow-up checklist, and links the reader to the detailed generated artifacts.

## Where outputs are written

The `--output-dir` argument controls where generated artifacts are written. The example command writes to `outputs/example/`. The repository also includes committed sample artifacts under `examples/example_outputs/`.

## Troubleshooting

### Missing manifest

If the pack does not contain `manifest.yaml` or `manifest.yml`, pass an explicit manifest with `--manifest PATH`. The manifest path must still resolve inside the pack directory.

### Missing referenced files

Missing files declared in the manifest are recorded as gaps in generated artifacts. Check the manifest path values and confirm the files exist under the pack directory.

### Malformed CSV

The current dataset profiler expects standard CSV files with headers. Check quoting, delimiters, and line endings if row or column results look unexpected.

### Path escapes rejected

Manifest and referenced paths must stay inside the pack directory. Absolute paths or `..` paths that escape the pack are rejected to prevent accidental reads outside the review pack.

### Hatchling or build dependency install issue in restricted environments

Editable installs use the build backend declared in `pyproject.toml`. In restricted environments, installing build dependencies such as `hatchling` may fail. If that happens, use an environment with package access, preinstall required build dependencies from an internal mirror, or run tests with `PYTHONPATH=src` as a local fallback.

## Optional LLM reviewer notes

The default command is deterministic and local-first. It writes `llm_reviewer_notes.json` with `llm_review_not_requested` and does not call an external API.

Install the optional OpenAI dependency only when you intend to request supplemental LLM reviewer notes:

```bash
python -m pip install -e ".[dev,llm]"
```

Example optional command:

```bash
python -m data_migration_readiness_review_agent.cli --pack examples/migration_pack --output-dir outputs/example --llm-review --llm-provider openai --llm-model YOUR_MODEL_NAME
```

The OpenAI SDK uses `OPENAI_API_KEY` from the environment by its normal behavior. You may set `OPENAI_MODEL` instead of passing `--llm-model`; do not write environment values into migration packs or artifacts. If the optional dependency, model name, or API call is unavailable, deterministic artifacts are still written and `llm_reviewer_notes.json` records a skipped or failed status with a sanitized warning.

The LLM receives a bounded context derived from `review_pack.json`: migration metadata, summary counts, capped findings, capped follow-up items, source artifact names, and boundary instructions. It does not receive raw dataset rows, preview rows, raw mismatch values, raw sensitive values, or API key values. Returned notes must be strict JSON, pass schema validation, and pass safe-language validation before inclusion.
