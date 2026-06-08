# Design principles

## Local-first

The workflow reads local migration pack files and writes local artifacts. It does not call cloud services or external APIs.

## Deterministic evidence first

The current workflow favors repeatable checks over generated judgment. Given the same migration pack and local path context, outputs should be stable except for path values recorded in the trace.

## Artifact-driven workflow

Each step writes an artifact with a narrow purpose. Reviewers can inspect details without reading code or rerunning the whole workflow.

## Bounded outputs

Dataset previews, distinct values, mismatch samples, missing-key samples, and warning summaries are bounded. This keeps artifacts small and reduces accidental exposure of full datasets.

## Safe language

Reviewer-facing outputs avoid verdict wording. The tool prepares findings and checklist items; it does not approve migration activity, decide go-live, certify compliance, or replace human reviewers.

## Path safety

Manifest and referenced paths must stay inside the migration pack directory. This protects local runs from accidentally reading files outside the intended evidence pack.

## Privacy caution

Sensitive-field review records indicators from field names and hints. It avoids writing raw sensitive values. Reviewers should still handle all generated artifacts according to their organization’s data-handling rules.

## Optional LLM later, bounded and non-authoritative

An LLM layer may be added later for summarization or routing of existing artifacts. It should not become the authority, and deterministic artifacts should remain the evidence base.

## Human reviewer remains final authority

The workflow supports review. It does not make automatic decisions. Human reviewers must interpret evidence and record decisions outside the tool.

## Why pandas is not used yet

The current CSV profiling uses the Python standard library to keep runtime dependencies small and behavior easy to inspect. Pandas may be useful later for broader data handling, but it is not needed for the current deterministic workflow.

## Why OpenAI and LangGraph are not dependencies yet

The current implementation has no LLM review and no graph orchestration. Avoiding OpenAI and LangGraph dependencies keeps local setup simpler and preserves a clear deterministic baseline.

## Why artifact outputs avoid dumping full datasets

Migration extracts can contain sensitive or business-critical data. The tool writes counts, schemas, bounded previews, and bounded samples rather than copying full source or target datasets into generated artifacts.

## Why the tool avoids approval and certification language

Generated artifacts can help reviewers find gaps and questions, but organizational decisions require context, ownership, controls, and accountability outside this CLI. The wording avoids implying that a local deterministic run can replace those processes.
