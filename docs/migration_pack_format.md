# Migration pack format

A migration pack is a local directory containing a manifest plus the files referenced by that manifest. By default, the CLI looks for `manifest.yaml` and then `manifest.yml` in the pack root. You can also pass `--manifest PATH`.

## Path rules

Paths in the manifest are relative to the migration pack directory. The tool rejects paths that resolve outside the pack directory. This includes absolute paths and `..` segments that escape the pack.

## Short manifest example

```yaml
migration:
  name: customer_account_migration
  owner: Example Data Migration Team
  source_system: legacy_crm
  target_system: new_customer_platform

datasets:
  - dataset_id: customers
    source_path: data/source_customers.csv
    target_path: data/target_customers.csv
    key_columns: [customer_id]
    row_count_tolerance: 0

mappings:
  - mapping_id: customer_mapping
    dataset_id: customers
    path: mappings/customer_mapping.csv

contracts:
  - contract_id: customer_contract
    dataset_id: customers
    path: contracts/customer_contract.yaml

test_results:
  - test_result_id: migration_test_results
    path: tests/test_results.csv

evidence:
  - evidence_id: rollback_plan
    evidence_type: rollback
    path: evidence/rollback_plan.md

sensitive_field_hints:
  - email
  - phone

readiness_dimensions:
  - schema_readiness
  - reconciliation
```

## Sections

### `migration`

Required. Describes the migration being reviewed. Common fields include `name`, `description`, `owner`, `source_system`, and `target_system`. These fields are carried into inventory and summary artifacts.

### `datasets`

Required for dataset profiling and reconciliation. Each dataset entry declares:

- `dataset_id`: stable identifier used by mappings and contracts.
- `source_path`: CSV source extract path relative to the pack.
- `target_path`: CSV target extract path relative to the pack.
- `key_columns`: optional list used for duplicate-key and key-overlap checks.
- `row_count_tolerance`: optional numeric tolerance used by row-count reconciliation.

### `mappings`

Optional. Each mapping entry declares a `mapping_id`, `dataset_id`, and CSV `path`. Mapping CSV files currently support direct source-field to target-field review using headers such as `source_field` and `target_field`.

### `contracts`

Optional. Each contract entry declares a `contract_id`, `dataset_id`, and YAML/YML `path`. Contract fields are reviewed against the observed target schema and target profile.

### `test_results`

Optional. Each entry declares a `test_result_id` and file `path`. CSV files receive structured header, row-count, and status-count review. Markdown, text, YAML, and YAML-like files are recorded as supplied metadata rather than deeply parsed test results.

### `evidence`

Optional. Each entry declares an `evidence_id`, `evidence_type`, and file `path`. Evidence files are used as presence evidence for expected types such as `migration_notes`, `cutover`, `rollback`, `risk`, and `acceptance`.

### `sensitive_field_hints`

Optional. A list of field-name hints that supplement deterministic column-name patterns. These hints help flag columns for human review without writing raw sensitive values.

### `readiness_dimensions`

Optional metadata. The current workflow records these declared labels but does not assess dimensions, score them, or produce a verdict.

## Supported file types currently

- CSV datasets.
- CSV mappings.
- YAML/YML contracts.
- CSV, Markdown, text, YAML, or YAML-like test evidence metadata.
- Markdown, text, YAML, or YAML-like evidence files as presence evidence.

## What is not parsed yet

The workflow does not parse Excel workbooks, databases, cloud storage locations, binary documents, PDFs, data warehouses, custom delimited files, or nested contract formats beyond the current YAML/YML contract structure. Non-CSV evidence documents are not evaluated for document quality or business meaning.
