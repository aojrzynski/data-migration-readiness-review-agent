# Reviewer workflow

This workflow is for humans using the generated artifacts. The tool prepares review material, but the reviewer remains the authority for interpretation and decisions.

## Practical review steps

1. **Open `reviewer_summary.md`.** Start with the run boundary, summary counts, grouped findings, artifact index, and follow-up checklist.
2. **Review summary counts.** Use counts to understand the size of the supplied pack and the number of generated findings.
3. **Work through the follow-up checklist.** Treat checklist items as prompts for human investigation, not as automated decisions.
4. **Use `review_pack.json` for structured finding details.** This is the compact machine-readable aggregation for filtering, tracking, or copying findings into another review process.
5. **Open source artifacts for detail.** Use the artifact index to inspect focused JSON files such as inventory, profiles, mapping review, contract review, reconciliation, sensitive-field indicators, test evidence, and evidence coverage.
6. **Check reconciliation findings.** Review row-count differences, missing source keys in target, unexpected target keys, skipped comparisons, and mismatch samples.
7. **Check mapping and contract findings.** Confirm that mappings reference expected source and target fields and that contract fields align with observed target columns.
8. **Check sensitive-field indicators and evidence coverage.** Confirm whether flagged columns need handling review and whether expected evidence types are declared and present.
9. **Review optional `llm_reviewer_notes.json` last when present.** Treat it as supplemental prompts derived from the deterministic review pack, not as a decision source.
10. **Record human decisions outside the tool.** Use your organization’s normal review records, ticketing system, risk log, change process, or meeting notes.

## Human authority boundary

The generated artifacts organize evidence and deterministic findings. They do not approve migration activity, decide go-live, certify compliance, certify privacy or legal status, or replace human reviewers.

Finding counts require interpretation. A low count does not remove the need for review, and a high count does not by itself define the outcome. Reviewers should inspect the underlying evidence, confirm context with owners, and document decisions outside this tool.
