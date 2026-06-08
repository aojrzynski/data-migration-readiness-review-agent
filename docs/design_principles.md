# Design principles

## Local-first by default

The default workflow reads local files and writes local artifacts. It does not make hidden external calls.

## Deterministic evidence first

The core review steps are deterministic. The same migration pack should produce the same review evidence, aside from local paths and run metadata.

## Artifact-driven review

Each stage writes a focused artifact. Reviewers can inspect the summary first, then open detailed JSON files when they need more context.

## JSON artifacts before Markdown summary

Structured JSON artifacts are written before `reviewer_summary.md`. The Markdown summary is a readable view over deterministic records.

## Bounded outputs

Outputs are intended to stay small. The tool records counts, headers, statuses, and bounded samples rather than dumping full datasets.

## Sensitive value caution

Sensitive-field indicators are prompts for review. They are not legal or privacy classifications. Raw sensitive values should not be copied into docs, prompts, tickets, or committed artifacts.

## Path safety

Manifest and referenced paths are expected to stay inside the migration pack. This keeps a pack from reaching into unrelated local files.

## Safe language

The tool should use evidence and follow-up language. It does not assess readiness, approve migration, decide go-live, certify compliance, certify security, certify privacy, certify legal status, certify governance status, or make a final decision.

## Optional LLM notes are non-authoritative

LLM reviewer notes are requested explicitly. They use bounded review-pack context, are written separately, and do not change deterministic findings.

## Optional LangGraph orchestration changes coordination only

The optional LangGraph path changes how stages are coordinated. It does not change artifact semantics or authority boundaries.

## Human review remains final authority

People must interpret findings, inspect source evidence, ask follow-up questions, and record decisions in the organization system outside this tool.

## No generated code execution

The tool reviews supplied files. It does not generate and execute remediation code.

## No hidden external calls

The default run is local. External LLM calls occur only when optional LLM review is explicitly requested and configured.
