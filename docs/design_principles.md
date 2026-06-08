# Design principles

## Local-first

The workflow reads local migration pack files and writes local artifacts. It does not call cloud services or external APIs.

## Deterministic evidence first

The current workflow favors repeatable checks over generated judgment. Given the same migration pack and local path context, outputs should be stable except for path values recorded in the trace.

## Artifact-driven workflow

Each step writes an artifact with a narrow purpose. Reviewers can inspect details without reading code or rerunning the whole workflow.

## Orchestration separation

The CLI stays thin: it parses arguments, validates simple command-line constraints, builds a run configuration, calls the selected orchestrator, and prints artifact paths and notes. The current supported orchestrator is the deterministic `standard` orchestrator. It owns the ordered workflow from manifest loading through artifact writing and trace creation.

Future optional orchestrators may be added behind this seam, but deterministic artifacts remain the authority for the local review workflow. Alternative orchestration must not turn the tool into a readiness assessor, approval engine, certification workflow, cloud connector, or automatic decision-maker.

## Bounded outputs

Dataset previews, distinct values, mismatch samples, missing-key samples, and warning summaries are bounded. This keeps artifacts small and reduces accidental exposure of full datasets.

## Safe language

Reviewer-facing outputs avoid verdict wording. The tool prepares findings and checklist items; it does not approve migration activity, decide go-live, certify compliance, or replace human reviewers.

## Path safety

Manifest and referenced paths must stay inside the migration pack directory. This protects local runs from accidentally reading files outside the intended evidence pack.

## Privacy caution

Sensitive-field review records indicators from field names and hints. It avoids writing raw sensitive values. Reviewers should still handle all generated artifacts according to their organization’s data-handling rules.

## Human reviewer remains final authority

The workflow supports review. It does not make automatic decisions. Human reviewers must interpret evidence and record decisions outside the tool.

## Why pandas is not used yet

The current CSV profiling uses the Python standard library to keep runtime dependencies small and behavior easy to inspect. Pandas may be useful later for broader data handling, but it is not needed for the current deterministic workflow.

## Why OpenAI is optional and LangGraph is absent

The default workflow does not require OpenAI and does not use graph orchestration. Keeping OpenAI in the optional `llm` dependency group preserves deterministic local setup by default, and LangGraph is not part of the current workflow.

## Why artifact outputs avoid dumping full datasets

Migration extracts can contain sensitive or business-critical data. The tool writes counts, schemas, bounded previews, and bounded samples rather than copying full source or target datasets into generated artifacts.

## Why the tool avoids approval and certification language

Generated artifacts can help reviewers find gaps and questions, but organizational decisions require context, ownership, controls, and accountability outside this CLI. The wording avoids implying that a local deterministic run can replace those processes.

## Optional LLM reviewer notes

The optional LLM layer is separate from deterministic review artifacts and is not authoritative. It uses bounded input generated from the in-memory review pack, not from raw generated files. The prompt context excludes raw rows, preview rows, raw sensitive values, raw mismatch values, local absolute paths where avoidable, and environment values.

LLM output is written only to `llm_reviewer_notes.json`. It is parsed as JSON, checked against the expected top-level schema, and rejected if safe-language validation finds positive verdict wording. The LLM notes do not modify `review_pack.json`, do not modify `reviewer_summary.md`, and do not make decisions for human reviewers.
