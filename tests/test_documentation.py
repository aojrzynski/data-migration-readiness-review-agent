from __future__ import annotations

from pathlib import Path

from data_migration_readiness_review_agent.safe_language import find_forbidden_terms

DOC_FILES = [
    Path("docs/overview.md"),
    Path("docs/local_usage.md"),
    Path("docs/migration_pack_format.md"),
    Path("docs/artifacts.md"),
    Path("docs/reviewer_workflow.md"),
    Path("docs/design_principles.md"),
]


def test_documentation_files_exist() -> None:
    for path in DOC_FILES:
        assert path.exists(), path


def test_readme_links_to_docs_and_names_first_artifact() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    for path in DOC_FILES:
        assert f"]({path.as_posix()})" in readme
    assert "reviewer_summary.md" in readme
    assert "best first artifact to open" in readme


def test_docs_do_not_use_unsafe_positive_verdict_language() -> None:
    for path in [Path("README.md"), *DOC_FILES]:
        text = path.read_text(encoding="utf-8")
        assert find_forbidden_terms(text) == [], path
