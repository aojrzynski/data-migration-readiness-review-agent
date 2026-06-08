# LLM reviewer notes

LLM reviewer notes are optional. The default command does not call an LLM.

## Install optional dependency

```bash
python -m pip install -e ".[dev,llm]"
```

## Run optional LLM review

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/llm-example --llm-review --llm-model YOUR_MODEL_NAME
```

Use `--llm-review` to request optional LLM reviewer notes. Use `--llm-model` to choose the model. If `--llm-model` is not supplied, `OPENAI_MODEL` can provide the default model.

The OpenAI client uses `OPENAI_API_KEY`. Do not write real key values in commands, manifests, docs, tickets, or committed artifacts.

## Input size

Use `--llm-max-input-chars` to bound the serialized review-pack context sent to the optional LLM:

```bash
data-migration-readiness-review --pack examples/migration_pack --output-dir outputs/llm-example --llm-review --llm-model YOUR_MODEL_NAME --llm-max-input-chars 12000
```

## Input policy

The optional LLM layer uses bounded `review_pack.json` context. It should not receive full raw datasets, raw sensitive values, API keys, or secrets.

## Output validation

LLM output is parsed and validated before it is written as `llm_reviewer_notes.json`. If output is missing, malformed, unavailable, or rejected, the deterministic artifacts still remain available.

## Possible statuses

`llm_reviewer_notes.json` can record these statuses:

- `llm_review_not_requested`
- `llm_review_skipped`
- `llm_review_completed`
- `llm_review_failed`
- `llm_review_rejected`

## What LLM notes can help with

LLM notes can help restate themes from the deterministic review pack, group follow-up prompts, and make reviewer notes easier to scan.

## What LLM notes cannot decide

LLM notes do not change deterministic findings. They do not assess readiness, approve migration, decide go-live, certify compliance, certify privacy, certify security, certify legal status, certify governance status, replace human review, or make a final decision.
