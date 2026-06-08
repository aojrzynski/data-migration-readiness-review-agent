"""
Manifest discovery, YAML loading, basic shape validation, and path safety checks. This
module verifies the pack references are safe to inspect, but it does not deeply parse
datasets, mappings, contracts, or evidence contents.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from data_migration_readiness_review_agent.models import LoadedManifest


class ManifestError(ValueError):
    """
    CLI-facing manifest problem. These errors describe malformed manifests, unsafe
    paths, or missing required manifest structure.
    """
    pass


LIST_SECTIONS = (
    "mappings",
    "contracts",
    "test_results",
    "evidence",
    "sensitive_field_hints",
    "readiness_dimensions",
)


def is_inside_path(child: Path, parent: Path) -> bool:
    """Return True when child is inside parent after both paths have already been resolved."""
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def resolve_inside_pack(pack_path: Path, candidate: Path, *, description: str) -> Path:
    """
    Resolve a manifest-referenced path and reject symlink or path traversal escapes
    outside the pack directory.
    """
    base_path = candidate if candidate.is_absolute() else pack_path / candidate
    resolved = base_path.expanduser().resolve(strict=False)
    # Resolve symlinks and parent-directory segments before enforcing the pack boundary.
    if not is_inside_path(resolved, pack_path):
        raise ManifestError(
            f"{description} must resolve inside the migration pack directory: {candidate}"
        )
    return resolved


def discover_manifest(pack_path: Path, manifest_path: Path | None) -> Path:
    """
    Find the manifest file for a pack. An explicit manifest path is resolved safely
    inside the pack; otherwise manifest.yaml is preferred before manifest.yml.
    """
    if manifest_path is not None:
        # Even explicit manifest paths must stay inside the pack for local-only review safety.
        resolved_manifest = resolve_inside_pack(
            pack_path,
            manifest_path,
            description="--manifest",
        )
        if not resolved_manifest.exists():
            raise ManifestError(f"--manifest path does not exist: {manifest_path}")
        if not resolved_manifest.is_file():
            raise ManifestError(f"--manifest must point to a file: {manifest_path}")
        return resolved_manifest

    # Prefer manifest.yaml for deterministic discovery, then accept the common .yml spelling.
    for file_name in ("manifest.yaml", "manifest.yml"):
        manifest_candidate = pack_path / file_name
        if manifest_candidate.exists() or manifest_candidate.is_symlink():
            resolved_manifest = resolve_inside_pack(
                pack_path,
                Path(file_name),
                description=file_name,
            )
            if not resolved_manifest.is_file():
                raise ManifestError(f"{file_name} must point to a file.")
            return resolved_manifest
    raise ManifestError(
        "No manifest found in pack directory. Expected manifest.yaml or manifest.yml."
    )


def load_manifest(pack_path: Path, manifest_path: Path | None = None) -> LoadedManifest:
    """
    Load, shape-check, and path-check the manifest before downstream review stages use
    it.
    """
    resolved_manifest_path = discover_manifest(pack_path, manifest_path)
    loaded = load_yaml_text(resolved_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ManifestError("Manifest must be a YAML mapping at the top level.")
    validate_manifest_shape(loaded)
    validate_referenced_paths(pack_path, loaded)
    return LoadedManifest(pack_path=pack_path, manifest_path=resolved_manifest_path, data=loaded)


def load_yaml_text(text: str) -> Any:
    """
    Parse manifest YAML with PyYAML when available, then fall back to limited local
    parsers for simple manifests.
    """
    yaml_spec = importlib.util.find_spec("yaml")
    if yaml_spec is not None:
        import yaml

        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ManifestError(f"Manifest YAML is malformed: {exc}") from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return parse_simple_yaml(text)
        except ValueError as exc:
            raise ManifestError(f"Manifest YAML is malformed: {exc}") from exc


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """
    Parse a small subset of YAML for environments without PyYAML. This fallback is
    intentionally limited and raises ManifestError through the caller on unsupported
    shapes.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    pending: list[tuple[int, dict[str, Any], str]] = []

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if "[" in line or "]" in line:
            raise ValueError("flow-style YAML is not supported by the fallback parser")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        while pending and indent <= pending[-1][0]:
            pending.pop()

        if line.startswith("- "):
            value_text = line[2:].strip()
            parent = stack[-1][1]
            if not isinstance(parent, list):
                if not pending:
                    raise ValueError(f"list item has no list parent: {raw_line}")
                _, pending_parent, pending_key = pending.pop()
                new_list: list[Any] = []
                pending_parent[pending_key] = new_list
                stack.append((indent - 1, new_list))
                parent = new_list
            if ":" in value_text:
                key, raw_value = split_key_value(value_text)
                item: dict[str, Any] = {key: parse_scalar(raw_value)}
                parent.append(item)
                stack.append((indent, item))
                if raw_value == "":
                    pending.append((indent, item, key))
            else:
                parent.append(parse_scalar(value_text))
            continue

        key, raw_value = split_key_value(line)
        parent = stack[-1][1]
        if not isinstance(parent, dict):
            raise ValueError(f"mapping item has no mapping parent: {raw_line}")
        if raw_value == "":
            parent[key] = {}
            pending.append((indent, parent, key))
            stack.append((indent, parent[key]))
        else:
            parent[key] = parse_scalar(raw_value)

    return root


def split_key_value(text: str) -> tuple[str, str]:
    """Split one simple YAML fallback line into a key and value."""
    if ":" not in text:
        raise ValueError(f"expected key/value pair: {text}")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"empty key in line: {text}")
    return key, value.strip()


def parse_scalar(value: str) -> Any:
    """Parse the small set of scalar values supported by the fallback YAML parser."""
    if value == "":
        return ""
    if value.isdecimal() or (value.startswith("-") and value[1:].isdecimal()):
        return int(value)
    if value in {"true", "false"}:
        return value == "true"
    return value.strip("\"'")


def require_non_empty_string(value: Any, field_name: str) -> None:
    """Raise ManifestError when a required manifest field is missing or blank."""
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"Manifest field {field_name} must be a non-empty string.")


def validate_manifest_shape(manifest: dict[str, Any]) -> None:
    """
    Check only the top-level manifest structure required by the workflow. Deep dataset
    and artifact review is left to later stages.
    """
    migration = manifest.get("migration")
    if not isinstance(migration, dict):
        raise ManifestError("Manifest must include a migration mapping.")
    require_non_empty_string(migration.get("name"), "migration.name")

    datasets = manifest.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ManifestError("Manifest field datasets must be a non-empty list.")

    # Dataset entries are the required anchors for source and target review stages.
    for index, dataset in enumerate(datasets):
        if not isinstance(dataset, dict):
            raise ManifestError(f"Manifest dataset at index {index} must be a mapping.")
        for field_name in ("dataset_id", "source_path", "target_path"):
            require_non_empty_string(dataset.get(field_name), f"datasets[{index}].{field_name}")
        key_columns = dataset.get("key_columns")
        if (
            not isinstance(key_columns, list)
            or not key_columns
            or not all(isinstance(column, str) and column.strip() for column in key_columns)
        ):
            raise ManifestError(
                f"Manifest field datasets[{index}].key_columns must be a non-empty list of strings."
            )

    # Optional sections must be lists when present so downstream loops stay predictable.
    for section in LIST_SECTIONS:
        value = manifest.get(section)
        if value is not None and not isinstance(value, list):
            raise ManifestError(f"Manifest field {section} must be a list when present.")


def validate_referenced_paths(pack_path: Path, manifest: dict[str, Any]) -> None:
    """
    Check that path-like manifest entries stay inside the migration pack. Missing files
    can still be recorded later as review gaps.
    """
    for dataset in manifest["datasets"]:
        # Existing files are checked later; this stage only rejects unsafe paths.
        resolve_inside_pack(
            pack_path, Path(dataset["source_path"]), description="dataset source_path"
        )
        resolve_inside_pack(
            pack_path, Path(dataset["target_path"]), description="dataset target_path"
        )

    for section in ("mappings", "contracts", "test_results", "evidence"):
        for index, item in enumerate(manifest.get(section, [])):
            if not isinstance(item, dict):
                raise ManifestError(f"Manifest item {section}[{index}] must be a mapping.")
            path = item.get("path")
            require_non_empty_string(path, f"{section}[{index}].path")
            # Missing referenced files become gaps in artifacts, not fatal load errors.
            resolve_inside_pack(pack_path, Path(path), description=f"{section}[{index}].path")
