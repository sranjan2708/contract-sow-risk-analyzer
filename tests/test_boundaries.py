"""
Boundary isolation and architectural rule verification tests.
Ensures engines remain pure, decoupled, and contract models are never redefined.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories to skip when scanning files
IGNORED_DIRS = {
    "venv",
    ".venv",
    "node_modules",
    "site-packages",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "dist",
    "build",
}


def _get_python_files(directory: Path) -> list[Path]:
    files: list[Path] = []
    for path in directory.rglob("*.py"):
        if any(ignored in path.parts for ignored in IGNORED_DIRS):
            continue
        files.append(path)
    return files


def test_engine_boundaries_no_forbidden_imports():
    """
    Verify pure engine isolation:
    - doc_engine, graph_engine, ai_engine must never import backend, fastapi, pymysql, sqlalchemy, or each other.
    """
    engine_specs = [
        {
            "name": "doc_engine",
            "dir": REPO_ROOT / "doc_engine",
            "forbidden": [
                r"\bimport\s+backend\b",
                r"\bfrom\s+backend\b",
                r"\bimport\s+fastapi\b",
                r"\bfrom\s+fastapi\b",
                r"\bimport\s+pymysql\b",
                r"\bfrom\s+pymysql\b",
                r"\bimport\s+sqlalchemy\b",
                r"\bfrom\s+sqlalchemy\b",
                r"\bimport\s+graph_engine\b",
                r"\bfrom\s+graph_engine\b",
                r"\bimport\s+ai_engine\b",
                r"\bfrom\s+ai_engine\b",
            ],
        },
        {
            "name": "graph_engine",
            "dir": REPO_ROOT / "graph_engine",
            "forbidden": [
                r"\bimport\s+backend\b",
                r"\bfrom\s+backend\b",
                r"\bimport\s+fastapi\b",
                r"\bfrom\s+fastapi\b",
                r"\bimport\s+pymysql\b",
                r"\bfrom\s+pymysql\b",
                r"\bimport\s+sqlalchemy\b",
                r"\bfrom\s+sqlalchemy\b",
                r"\bimport\s+doc_engine\b",
                r"\bfrom\s+doc_engine\b",
                r"\bimport\s+ai_engine\b",
                r"\bfrom\s+ai_engine\b",
            ],
        },
        {
            "name": "ai_engine",
            "dir": REPO_ROOT / "ai_engine",
            "forbidden": [
                r"\bimport\s+backend\b",
                r"\bfrom\s+backend\b",
                r"\bimport\s+fastapi\b",
                r"\bfrom\s+fastapi\b",
                r"\bimport\s+pymysql\b",
                r"\bfrom\s+pymysql\b",
                r"\bimport\s+sqlalchemy\b",
                r"\bfrom\s+sqlalchemy\b",
                r"\bimport\s+doc_engine\b",
                r"\bfrom\s+doc_engine\b",
                r"\bimport\s+graph_engine\b",
                r"\bfrom\s+graph_engine\b",
            ],
        },
    ]

    violations: list[str] = []

    for spec in engine_specs:
        py_files = _get_python_files(spec["dir"])
        for file_path in py_files:
            content = file_path.read_text(encoding="utf-8")
            for pattern in spec["forbidden"]:
                if re.search(pattern, content):
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)} violates boundary with pattern: {pattern}"
                    )

    assert not violations, "\n".join(violations)


def test_backend_never_imports_sqlalchemy():
    """Backend must strictly use raw parameterized SQL (PyMySQL), never SQLAlchemy."""
    backend_dir = REPO_ROOT / "backend"
    py_files = _get_python_files(backend_dir)
    forbidden_patterns = [
        r"\bimport\s+sqlalchemy\b",
        r"\bfrom\s+sqlalchemy\b",
    ]

    violations: list[str] = []
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if re.search(pattern, content):
                violations.append(
                    f"{file_path.relative_to(REPO_ROOT)} illegally imports SQLAlchemy: {pattern}"
                )

    assert not violations, "\n".join(violations)


def test_no_contract_model_redefined_outside_shared():
    """
    Contract models must only ever be defined in shared/contracts.py.
    No file outside shared/ may define class ParsedDocument|ClauseGraph|AnalysisResult|ComparisonResult|RiskFinding|Clause.
    """
    forbidden_class_pattern = re.compile(
        r"^\s*class\s+(ParsedDocument|ClauseGraph|AnalysisResult|ComparisonResult|RiskFinding|Clause)\b",
        re.MULTILINE,
    )

    violations: list[str] = []
    for path in REPO_ROOT.rglob("*.py"):
        if any(ignored in path.parts for ignored in IGNORED_DIRS):
            continue
        # Skip shared directory where contracts are legally defined
        if "shared" in path.parts:
            continue

        content = path.read_text(encoding="utf-8")
        matches = forbidden_class_pattern.findall(content)
        if matches:
            violations.append(
                f"{path.relative_to(REPO_ROOT)} illegally defines contract model class(es): {', '.join(matches)}"
            )

    assert not violations, "\n".join(violations)
