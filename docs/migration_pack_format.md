# Migration pack format

A migration pack is a local folder with a manifest and the evidence files referenced by that manifest. Paths in the manifest are relative to the pack and must stay inside the pack.

## Example directory layout

```text
migration_pack/
  manifest.yaml
  data/
    source_customers.csv
    target_customers.csv
  mappings/
    customer_mapping.csv
  contracts/
    customer_contract.yaml
  tests/
    test_results.csv
  evidence/
    cutover_plan.md
    rollback_plan.md
```

## Manifest location

By default, the CLI looks for `manifest.yaml` or `manifest.yml` in the pack. You can pass `--manifest` to use an explicit manifest path.

## Required and optional sections

Required:

- `migration`
- `datasets`

Optional:

- `mappings`
- `contracts`
- `test_results`
- `evidence`
- `sensitive_field_hints`
- `readiness_dimensions`

## Short YAML example

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
    key_columns:
      - customer_id
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
  - evidence_id: cutover_plan
    evidence_type: cutover
    path: evidence/cutover_plan.md

sensitive_field_hints:
  - email
  - phone

readiness_dimensions:
  - schema_readiness
  - reconciliation
```

## Section notes

### `migration`

Describes the migration name, owner, source system, target system, and optional description. It is used for traceability in artifacts.

### `datasets`

Declares source and target CSV files. Each dataset should have a `dataset_id`, `source_path`, `target_path`, and optional `key_columns` and `row_count_tolerance`.

### `mappings`

Declares CSV mapping files. Mapping files are parsed and checked against observed source and target schemas.

### `contracts`

Declares YAML or YML contract files. Contract fields are parsed and checked against target schemas and dataset profiles.

### `test_results`

Declares test evidence files. CSV test result files are structurally reviewed. Other files may be inventoried as declared evidence without deep parsing.

### `evidence`

Declares supporting files such as migration notes, risk logs, cutover notes, rollback notes, and acceptance notes. These files are inventoried for presence and evidence coverage.

### `sensitive_field_hints`

Lists words that should be treated as sensitive-field indicators when they appear in column names. Indicators are prompts for human review, not classifications.

### `readiness_dimensions`

Lists expected evidence dimensions for coverage review. The tool checks declared and present evidence against these expectations. It does not assess readiness.

## Supported file types

Parsed deeply:

- CSV datasets.
- CSV mappings.
- YAML/YML contracts.
- CSV test result files.

Inventoried or checked for declared presence:

- Evidence files such as Markdown or text notes.
- Non-CSV test evidence files.

## Not supported yet

- XLSX, Parquet, Avro, JSONL, or database tables as profiled datasets.
- PDF, DOCX, OCR, image extraction, or scanned evidence parsing.
- Database, cloud, or SaaS connectors.
- Transformation execution or remediation.
