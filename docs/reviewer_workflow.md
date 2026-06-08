# Reviewer workflow

This page explains how a human reviewer can use the generated artifacts. The tool prepares evidence and follow-up prompts. It does not replace human review.

## Start with `reviewer_summary.md`

Open `reviewer_summary.md` first. It gives the run boundary, summary counts, grouped findings, artifact index, and follow-up checklist.

## Understand the scope boundary

The artifacts describe the files declared in the migration pack. They do not prove that every workplace evidence item exists. If a file was not supplied or declared, the reviewer should follow up outside the tool.

## Use summary counts

Use counts to understand the pack size and finding volume. Counts help with triage. They are not a final decision.

## Work through the follow-up checklist

Treat checklist items as review prompts. Assign owners, ask questions, request missing evidence, and record outcomes in the organization review process.

## Investigate reconciliation findings

Open `reconciliation_results.json` for row-count differences, key-overlap details, skipped checks, and bounded mismatch samples. Use source evidence and business context to interpret differences.

## Investigate mapping and contract findings

Open `mapping_review.json` and `contract_review.json` to see whether declared fields line up with observed schemas. Confirm expected transformations and contract rules with data owners.

## Investigate sensitive-field indicators

Open `sensitive_field_review.json` to see column-name and manifest-hint indicators. Treat these as prompts to check handling requirements with the right owner.

## Check test evidence and evidence coverage

Open `test_evidence_review.json` for supplied test-evidence structure. Open `evidence_coverage_review.json` to see whether expected evidence types were declared and present.

## Use LLM notes only as supplemental notes

Open `llm_reviewer_notes.json` last, and only as supplemental notes. LLM notes do not change deterministic findings and are not a decision source.

## Record human decisions outside the tool

Record decisions, risk acceptance, evidence requests, meeting notes, and signoffs in the organization system outside this tool.

## Authority boundary

The generated artifacts organize evidence and deterministic findings. The tool does not assess readiness, approve migration, decide go-live, certify compliance, certify privacy or legal status, or replace human reviewers.
