"""Project creation logic for pypt – Python port of init.ps1."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

_SCANCODE_INDEX_URL = "https://scancode-licensedb.aboutcode.org/index.json"
_SCANCODE_BASE_URL = "https://scancode-licensedb.aboutcode.org/"

_LICENSE_CLASSIFIERS: dict[str, str] = {
    "MIT": "License :: OSI Approved :: MIT License",
    "Apache-2.0": "License :: OSI Approved :: Apache Software License",
    "BSD-3-Clause": "License :: OSI Approved :: BSD License",
    "BSD-2-Clause": "License :: OSI Approved :: BSD License",
    "LGPL-3.0": "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    "LGPL-3.0-or-later": "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    "LGPL-2.1": "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
    "LGPL-2.1-or-later": "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
    "GPL-3.0": "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    "GPL-3.0-or-later": "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    "GPL-2.0": "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
    "GPL-2.0-or-later": "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
    "AGPL-3.0": "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "AGPL-3.0-or-later": "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "MPL-2.0": "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
    "ISC": "License :: OSI Approved :: ISC License (ISCL)",
    "Unlicense": "License :: Public Domain",
}

_DEFAULT_LICENSE_ID = "LGPL-3.0-or-later"
_DEFAULT_LICENSE_CLASSIFIER = _LICENSE_CLASSIFIERS[_DEFAULT_LICENSE_ID]

_GITIGNORE_ENTRIES = [
    "__pycache__/",
    "*.py[cod]",
    "*$py.class",
    ".venv/",
    "venv/",
    "env/",
    ".python-version",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pyright/",
    ".coverage",
    "coverage.xml",
    "htmlcov/",
    "build/",
    "dist/",
    ".eggs/",
    "*.egg-info/",
    "pip-wheel-metadata/",
    ".ipynb_checkpoints/",
]


class GitAuthor(NamedTuple):
    """Git author information."""

    name: str
    email: str


def check_uv() -> None:
    """Raise SystemExit if uv is not available on PATH."""
    if shutil.which("uv") is None:
        print(
            "error: 'uv' not found on PATH.\n"
            "Install it from https://docs.astral.sh/uv/getting-started/installation/",
            file=sys.stderr,
        )
        raise SystemExit(1)


def get_git_author() -> GitAuthor:
    """Return the git user name/email, falling back to placeholders."""
    name = ""
    email = ""
    if shutil.which("git"):
        try:
            name = subprocess.check_output(
                ["git", "config", "--get", "user.name"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except subprocess.CalledProcessError:
            pass
        try:
            email = subprocess.check_output(
                ["git", "config", "--get", "user.email"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except subprocess.CalledProcessError:
            pass
    return GitAuthor(name=name or "Your Name", email=email or "you@example.com")


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command, raising SystemExit on non-zero exit."""
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def init_project(project_name: str, python_version: str, cwd: Path) -> Path:
    """Run ``uv init --lib`` and return the created project directory."""
    _run(["uv", "init", "--lib", "--python", python_version, project_name], cwd=cwd)
    # uv may create the directory using the project name directly or with
    # hyphens replaced by underscores.
    for candidate in (project_name, project_name.replace("-", "_")):
        project_dir = cwd / candidate
        if project_dir.is_dir():
            return project_dir
    raise SystemExit(f"error: project directory not found after 'uv init' for '{project_name}'")


def write_pyproject(
    project_dir: Path,
    project_name: str,
    package_name: str,
    python_version: str,
    description: str,
    author: GitAuthor,
) -> None:
    """Overwrite pyproject.toml with the canonical pypt template."""
    today = datetime.now().strftime("%Y.%m.%d")
    version = f"{today}.00"
    py_no_dot = python_version.replace(".", "")
    license_classifier = _DEFAULT_LICENSE_CLASSIFIER

    lines = [
        "[project]",
        f'name = "{project_name}"',
        f'version = "{version}"',
        f'description = "{description}"',
        'readme = "README.md"',
        f'license = "{_DEFAULT_LICENSE_ID}"',
        f'authors = [{{ name = "{author.name}", email = "{author.email}" }}]',
        f'requires-python = ">={python_version}"',
        "classifiers = [",
        f'  "{license_classifier}",',
        '  "Operating System :: Microsoft :: Windows",',
        '  "Programming Language :: Python :: 3",',
        f'  "Programming Language :: Python :: {python_version}",',
        "]",
        'dependencies = ["beartype>=0.22.9"]',
        "",
        "[project.optional-dependencies]",
        'dev = ["pytest>=9.0.3", "pytest-cov>=7.1.0", "pytest-sugar>=1.1.1"]',
        "",
        "[build-system]",
        'requires = ["uv_build>=0.11.6"]',
        'build-backend = "uv_build"',
        "",
        "[tool.basedpyright]",
        'venvPath = "."',
        'venv = ".venv"',
        f'include = ["src", "src/{package_name}/tests"]',
        f'pythonVersion = "{python_version}"',
        'reportUnusedCallResult = "none"',
        'reportAny = "none"',
        'reportExplicitAny = "none"',
        'reportImplicitStringConcatenation = "none"',
        'reportUnusedFunction = "none"',
        'reportMissingParameterType = "none"',
        'reportUnknownParameterType = "none"',
        'reportUnknownVariableType = "none"',
        'reportUnknownArgumentType = "none"',
        'reportUnknownMemberType = "none"',
        "",
        "[tool.ruff]",
        "line-length = 120",
        f'target-version = "py{py_no_dot}"',
        "",
        "[tool.ruff.lint.isort]",
        "force-single-line = true",
        "",
        "[tool.coverage.run]",
        f'source = ["src/{package_name}"]',
        f'omit = ["src/{package_name}/tests/*"]',
        "",
        "[tool.ty.src]",
        'exclude = ["typings"]',
    ]
    pyproject_path = project_dir / "pyproject.toml"
    pyproject_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated {pyproject_path} with project/build/tool settings.")


def create_smoke_test(project_dir: Path, package_name: str) -> None:
    """Create a minimal importable smoke test."""
    tests_dir = project_dir / "src" / package_name / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    smoke_test = tests_dir / "test_smoke.py"
    lines = [
        "import importlib",
        "",
        "",
        "def test_package_importable() -> None:",
        f'    module = importlib.import_module("{package_name}")',
        "    assert module is not None",
    ]
    smoke_test.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Created smoke test at {smoke_test}")


def create_venv(project_dir: Path, python_version: str) -> None:
    """Create a virtual environment inside the project directory."""
    _run(["uv", "venv", "--python", python_version], cwd=project_dir)


def setup_gitignore(project_dir: Path) -> None:
    """Create or augment .gitignore with Python-standard entries."""
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("\n".join(_GITIGNORE_ENTRIES) + "\n", encoding="utf-8")
        print(f"Created {gitignore} with Python defaults.")
    else:
        existing = gitignore.read_text(encoding="utf-8").splitlines()
        missing = [e for e in _GITIGNORE_ENTRIES if e and e not in existing]
        if missing:
            with gitignore.open("a", encoding="utf-8") as fh:
                fh.write("\n" + "\n".join(missing) + "\n")
            print(f"Updated {gitignore} with {len(missing)} missing Python defaults.")
        else:
            print(f"{gitignore} already contains Python defaults.")


def setup_yamllint(project_dir: Path) -> None:
    """Create .yamllint if it does not exist."""
    yamllint = project_dir / ".yamllint"
    if not yamllint.exists():
        lines = [
            "---",
            "extends: default",
            "",
            "rules:",
            "  new-lines: disable",
            "  document-start: disable",
            "  line-length: disable",
        ]
        yamllint.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Created {yamllint}.")
    else:
        print(f"{yamllint} already exists, leaving it unchanged.")


def setup_vscode(project_dir: Path) -> None:
    """Write VS Code workspace settings."""
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings = vscode_dir / "settings.json"
    lines = [
        "{",
        '  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",',
        '  "python.terminal.activateEnvironment": true,',
        '  "python.analysis.extraPaths": ["${workspaceFolder}/src"],',
        '  "python.analysis.typeCheckingMode": "off",',
        '  "basedpyright.analysis.diagnosticMode": "workspace",',
        '  "editor.formatOnSave": true,',
        '  "ruff.nativeServer": "on",',
        '  "[python]": {',
        '    "editor.defaultFormatter": "charliermarsh.ruff",',
        '    "editor.codeActionsOnSave": {',
        '      "source.fixAll.ruff": "explicit",',
        '      "source.organizeImports.ruff": "explicit"',
        "    }",
        "  }",
        "}",
    ]
    settings.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote VS Code settings to {settings}")


def setup_justfiles(project_dir: Path, package_name: str) -> None:
    """Create the justfile and .justfiles/ directory with all sub-recipes."""
    justfiles_dir = project_dir / ".justfiles"
    justfiles_dir.mkdir(exist_ok=True)

    # --- prek.just ---
    prek_just = (
        "prek-init:\n"
        "    if (-not (Test-Path 'pyproject.toml')) { throw 'pyproject.toml not found. Run just init first.' }; \\\n"
        "    $projectNameMatch = Select-String -Path 'pyproject.toml' -Pattern '^\\s*name\\s*=\\s*\"([^\\\"]+)\"'"
        " -AllMatches | Select-Object -First 1;"
        " if (-not $projectNameMatch -or $projectNameMatch.Matches.Count -eq 0) { throw 'project.name not found in pyproject.toml.' };"
        " $projectName = $projectNameMatch.Matches[0].Groups[1].Value; \\\n"
        "    $packageName = $projectName -replace '-', '_'; \\\n"
        "    uv add --optional dev prek; \\\n"
        f"    $packageNameVar = '{package_name}'; \\\n"
        "    $lines = @( \\\n"
        "    'default_language_version:', \\\n"
        "    '  python: python3.14', \\\n"
        "    'repos:', \\\n"
        "    '  - repo: local', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: prek-auto-update', \\\n"
        "    '        name: prek-auto-update', \\\n"
        "    '        entry: uv run prek auto-update', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '        fail_fast: true', \\\n"
        "    '  - repo: https://github.com/bwhmather/ssort', \\\n"
        "    '    rev: 0.16.0', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: ssort', \\\n"
        "    '  - repo: https://github.com/pre-commit/pre-commit-hooks', \\\n"
        "    '    rev: v6.0.0', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: fix-byte-order-marker', \\\n"
        "    '      - id: check-merge-conflict', \\\n"
        "    '      - id: end-of-file-fixer', \\\n"
        r"    '        exclude: ^static/.*\.svg$', \\" + "\n"
        "    '      - id: trailing-whitespace', \\\n"
        "    '      - id: mixed-line-ending', \\\n"
        r"    '        exclude: ^static/.*\.svg$', \\" + "\n"
        "    '      - id: check-yaml', \\\n"
        "    '      - id: check-toml', \\\n"
        "    '      - id: check-added-large-files', \\\n"
        r"    '        exclude: ^tests/media/.*\.cbz$', \\" + "\n"
        "    '      - id: debug-statements', \\\n"
        "    '        language_version: python3.14', \\\n"
        "    '      - id: check-executables-have-shebangs', \\\n"
        "    '      - id: check-shebang-scripts-are-executable', \\\n"
        "    '  - repo: https://github.com/google/yamlfmt', \\\n"
        "    '    rev: v0.21.0', \\\n"
        "    '    hooks:', \\\n"
        r"    '      - id: yamlfmt', \\" + "\n"
        r"    '        files: \.(yml|yaml)$', \\" + "\n"
        "    '  - repo: https://github.com/adrienverge/yamllint', \\\n"
        "    '    rev: v1.38.0', \\\n"
        "    '    hooks:', \\\n"
        r"    '      - id: yamllint', \\" + "\n"
        r"    '        files: \.(yml|yaml)$', \\" + "\n"
        "    '  - repo: https://github.com/shellcheck-py/shellcheck-py', \\\n"
        "    '    rev: v0.11.0.1', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: shellcheck', \\\n"
        "    '  - repo: https://github.com/scop/pre-commit-shfmt', \\\n"
        "    '    rev: v3.13.1-1', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: shfmt', \\\n"
        "    '  - repo: https://github.com/crate-ci/typos', \\\n"
        "    '    rev: v1.45.0', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: typos', \\\n"
        "    '  - repo: https://github.com/executablebooks/mdformat', \\\n"
        "    '    rev: 1.0.0', \\\n"
        "    '    hooks:', \\\n"
        r"    '      - id: mdformat', \\" + "\n"
        r"    '        files: \.md$', \\" + "\n"
        "    '  - repo: https://github.com/DavidAnson/markdownlint-cli2', \\\n"
        "    '    rev: v0.22.0', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: markdownlint-cli2', \\\n"
        "    '  - repo: https://github.com/ComPWA/taplo-pre-commit', \\\n"
        "    '    # toml formatter', \\\n"
        "    '', \\\n"
        "    '    rev: v0.9.3', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: taplo-format', \\\n"
        "    '      - id: taplo-lint', \\\n"
        "    '  - repo: https://github.com/asottile/pyupgrade', \\\n"
        "    '    rev: v3.21.2', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: pyupgrade', \\\n"
        "    '        language_version: python3.14', \\\n"
        "    '        args: [--py314-plus, --keep-runtime-typing]', \\\n"
        r"    '        files: ^(src|tests)/.*\.py$', \\" + "\n"
        "    '  - repo: https://github.com/hadialqattan/pycln', \\\n"
        "    '    rev: v2.6.0', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: pycln', \\\n"
        "    '        language_version: python3.14', \\\n"
        "    '        args: [src, tests]', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '  - repo: https://github.com/astral-sh/ruff-pre-commit', \\\n"
        "    '    rev: v0.15.10', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: ruff-check', \\\n"
        "    '        language_version: python3.14', \\\n"
        "    '        args: [--fix, --exclude, typings]', \\\n"
        r"    '        files: ^(src|tests)/.*\.py$', \\" + "\n"
        "    '      - id: ruff-format', \\\n"
        "    '        language_version: python3.14', \\\n"
        "    '        args: [--exclude, typings]', \\\n"
        r"    '        files: ^(src|tests)/.*\.py$', \\" + "\n"
        "    '      - id: ruff-check', \\\n"
        "    '        name: ruff-check-post-format', \\\n"
        "    '        language_version: python3.14', \\\n"
        "    '        args: [--exclude, typings]', \\\n"
        r"    '        files: ^(src|tests)/.*\.py$', \\" + "\n"
        "    '  - repo: local', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: autopep695-format', \\\n"
        "    '        name: autopep695-format', \\\n"
        "    '        entry: uvx autopep695 format', \\\n"
        "    '        language: system', \\\n"
        r"    '        files: ^(src|tests)/.*\.py$', \\" + "\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '      - id: vulture', \\\n"
        "    '        name: vulture', \\\n"
        "    '        entry: |', \\\n"
        "    '          uvx --python 3.14 vulture src --min-confidence 80 --ignore-names', \\\n"
        "    '          dst,secure,httponly,samesite,unc_path,package_family_name,logo44x44', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '      - id: deptry', \\\n"
        "    '        name: deptry', \\\n"
        "    '        entry: uvx deptry . --ignore DEP001,DEP002', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '      - id: refurb', \\\n"
        "    '        name: refurb', \\\n"
        "    '        entry: uvx ruff check --select FURB --ignore FURB110 src tests', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '      - id: basedpyright', \\\n"
        "    '        name: basedpyright', \\\n"
        "    '        entry: uvx basedpyright', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '      - id: ty-check', \\\n"
        "    '        name: ty-check', \\\n"
        "    '        entry: uvx ty check', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '      - id: pip-audit', \\\n"
        "    '        name: pip-audit', \\\n"
        "    '        entry: uvx pip-audit', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        f"    ('        entry: uv run pytest --doctest-modules --cov=src/' + $packageNameVar + ' --cov-report=term-missing --cov-fail-under=100 src/' + $packageNameVar), \\\n"
        "    '      - id: coverage-100', \\\n"
        "    '        name: coverage-100', \\\n"
        "    '        language: system', \\\n"
        "    '        pass_filenames: false', \\\n"
        "    '        always_run: true', \\\n"
        "    '        stages: [pre-commit]', \\\n"
        "    '  - repo: https://github.com/Yelp/detect-secrets', \\\n"
        "    '    rev: v1.5.0', \\\n"
        "    '    hooks:', \\\n"
        "    '      - id: detect-secrets', \\\n"
        "    '        language_version: python3.14', \\\n"
        '    \'        args: ["--baseline", ".secrets.baseline"]\', \\\n'
        "    '        stages: [pre-commit]' \\\n"
        "    ); \\\n"
        "    $preCommitYaml = $lines -join \"`n\"; \\\n"
        "    $utf8NoBom = New-Object System.Text.UTF8Encoding($false); \\\n"
        "    [System.IO.File]::WriteAllText('.pre-commit-config.yaml', $preCommitYaml, $utf8NoBom); \\\n"
        "    uv run prek install\n"
    )
    (justfiles_dir / "prek.just").write_text(prek_just, encoding="utf-8")

    # --- license.just ---
    license_just = (
        "# Select and download a software license from scancode-licensedb.\n"
        "license:\n"
        "    $indexUrl = 'https://scancode-licensedb.aboutcode.org/index.json'; \\\n"
        "    $baseUrl = 'https://scancode-licensedb.aboutcode.org/'; \\\n"
        "    $all = Invoke-RestMethod -Uri $indexUrl -TimeoutSec 30; \\\n"
        "    $licenses = $all | Where-Object { \\\n"
        "    -not $_.is_exception -and -not $_.is_deprecated -and $_.license \\\n"
        "    } | Sort-Object spdx_license_key, license_key; \\\n"
        "    if (-not $licenses -or $licenses.Count -eq 0) { throw 'No licenses found in remote index.' }; \\\n"
        "    Write-Host ('Found ' + $licenses.Count + ' licenses.'); \\\n"
        "    $query = Read-Host 'Filter licenses by text (blank for all)'; \\\n"
        "    if ($query) { \\\n"
        "    $licenses = $licenses | Where-Object { \\\n"
        "    (($_.spdx_license_key) -and ($_.spdx_license_key -match [regex]::Escape($query))) -or \\\n"
        "    (($_.license_key) -and ($_.license_key -match [regex]::Escape($query))) \\\n"
        "    }; \\\n"
        "    if (-not $licenses -or $licenses.Count -eq 0) { throw ('No licenses matched filter: ' + $query) } \\\n"
        "    }; \\\n"
        "    Write-Host ('Showing ' + $licenses.Count + ' licenses.'); \\\n"
        "    for ($i = 0; $i -lt $licenses.Count; $i++) { \\\n"
        "    $name = if ($licenses[$i].spdx_license_key) { $licenses[$i].spdx_license_key } else { $licenses[$i].license_key }; \\\n"
        "    Write-Host ([string]($i + 1) + '. ' + $name) \\\n"
        "    }; \\\n"
        "    $selection = Read-Host 'Enter number'; \\\n"
        "    [int]$parsed = 0; \\\n"
        "    if (-not [int]::TryParse($selection, [ref]$parsed)) { throw 'Invalid selection.' }; \\\n"
        "    $selectedIndex = $parsed - 1; \\\n"
        "    if ($selectedIndex -lt 0 -or $selectedIndex -ge $licenses.Count) { throw 'Selection out of range.' }; \\\n"
        "    $chosen = $licenses[$selectedIndex]; \\\n"
        "    $fileName = $chosen.license; \\\n"
        "    $url = $baseUrl + $fileName; \\\n"
        "    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile 'LICENSE'; \\\n"
        "    $chosenName = if ($chosen.spdx_license_key) { $chosen.spdx_license_key } else { $chosen.license_key }; \\\n"
        "    Write-Host ('Downloaded ' + $chosenName + ' to LICENSE')\n"
    )
    (justfiles_dir / "license.just").write_text(license_just, encoding="utf-8")

    # --- github_actions.just ---
    github_actions_just = (
        "# Create GitHub automation files (.github/dependabot.yml and workflows).\n"
        "github-actions-init:\n"
        "    $pyprojectPath = 'pyproject.toml'; \\\n"
        "    if (-not (Test-Path $pyprojectPath)) { throw 'pyproject.toml not found. Run this from your project root.' }; \\\n"
        "    $pythonVersion = '3.14'; \\\n"
        "    $requiresMatch = Select-String -Path $pyprojectPath -Pattern '^requires-python\\s*=\\s*\">=([0-9]+\\.[0-9]+)\"'"
        " -AllMatches | Select-Object -First 1; \\\n"
        "    if ($requiresMatch -and $requiresMatch.Matches.Count -gt 0) { $pythonVersion = $requiresMatch.Matches[0].Groups[1].Value }; \\\n"
        "    $targetGithubDir = '.github'; \\\n"
        "    $targetWorkflowsDir = Join-Path $targetGithubDir 'workflows'; \\\n"
        "    if (-not (Test-Path $targetGithubDir)) { New-Item -ItemType Directory -Path $targetGithubDir | Out-Null }; \\\n"
        "    if (-not (Test-Path $targetWorkflowsDir)) { New-Item -ItemType Directory -Path $targetWorkflowsDir | Out-Null }; \\\n"
        "    $dependabotPath = Join-Path $targetGithubDir 'dependabot.yml'; \\\n"
        "    $lintFormatPath = Join-Path $targetWorkflowsDir 'lint-format.yml'; \\\n"
        "    $publishPath = Join-Path $targetWorkflowsDir 'publish-pypi.yml'; \\\n"
        "    $qualityPath = Join-Path $targetWorkflowsDir 'quality-security.yml'; \\\n"
        "    $testsPath = Join-Path $targetWorkflowsDir 'tests.yml'; \\\n"
        "    $typecheckPath = Join-Path $targetWorkflowsDir 'typecheck.yml'; \\\n"
        "    $dependabotLines = @( \\\n"
        "    'version: 2', \\\n"
        "    'updates:', \\\n"
        "    '  - package-ecosystem: \"github-actions\"', \\\n"
        "    '    directory: \"/\"', \\\n"
        "    '    schedule:', \\\n"
        "    '      interval: \"weekly\"', \\\n"
        "    '    open-pull-requests-limit: 10', \\\n"
        "    '  - package-ecosystem: \"uv\"', \\\n"
        "    '    directory: \"/\"', \\\n"
        "    '    schedule:', \\\n"
        "    '      interval: \"weekly\"', \\\n"
        "    '    open-pull-requests-limit: 10' \\\n"
        "    ); \\\n"
        "    $lintFormatLines = @( \\\n"
        "    'name: Lint and Format', \\\n"
        "    '\"on\":', \\\n"
        "    '  pull_request:', \\\n"
        "    '  push:', \\\n"
        "    '    branches: [main]', \\\n"
        "    '  workflow_dispatch:', \\\n"
        "    'permissions:', \\\n"
        "    '  contents: read', \\\n"
        "    'jobs:', \\\n"
        "    '  lint-format:', \\\n"
        "    '    name: Lint and format checks', \\\n"
        "    '    runs-on: ubuntu-latest', \\\n"
        "    '    timeout-minutes: 30', \\\n"
        "    '    steps:', \\\n"
        "    '      - name: Checkout repository', \\\n"
        "    '        uses: actions/checkout@v6', \\\n"
        "    '      - name: Set up Python', \\\n"
        "    '        uses: actions/setup-python@v6', \\\n"
        "    '        with:', \\\n"
        "    ('          python-version: \"' + $pythonVersion + '\"'), \\\n"
        "    '      - name: Set up uv', \\\n"
        "    '        uses: astral-sh/setup-uv@v7', \\\n"
        "    '      - name: Install project with dev dependencies', \\\n"
        "    '        run: uv sync --extra dev', \\\n"
        "    '      - name: Run lint and format hooks', \\\n"
        "    '        run: |', \\\n"
        "    '          uv run prek run ssort --all-files', \\\n"
        "    '          uv run prek run fix-byte-order-marker check-merge-conflict \\', \\\n"
        "    '            end-of-file-fixer trailing-whitespace mixed-line-ending --all-files', \\\n"
        "    '          uv run prek run check-yaml check-toml check-added-large-files \\', \\\n"
        "    '            check-executables-have-shebangs \\', \\\n"
        "    '            check-shebang-scripts-are-executable \\', \\\n"
        "    '            --all-files', \\\n"
        "    '          uv run prek run yamlfmt yamllint --all-files', \\\n"
        "    '          uv run prek run typos mdformat markdownlint-cli2 --all-files', \\\n"
        "    '          uv run prek run taplo-format taplo-lint --all-files', \\\n"
        "    '          uv run prek run pyupgrade pycln autopep695-format --all-files', \\\n"
        "    '          uv run prek run ruff-check ruff-format ruff-check-post-format \\', \\\n"
        "    '            refurb --all-files' \\\n"
        "    ); \\\n"
        "    $publishLines = @( \\\n"
        "    'name: Publish to PyPI', \\\n"
        "    '\"on\":', \\\n"
        "    '  release:', \\\n"
        "    '    types: [published]', \\\n"
        "    '  workflow_dispatch:', \\\n"
        "    'permissions:', \\\n"
        "    '  contents: read', \\\n"
        "    'jobs:', \\\n"
        "    '  build:', \\\n"
        "    '    name: Build distributions', \\\n"
        "    '    runs-on: ubuntu-latest', \\\n"
        "    '    steps:', \\\n"
        "    '      - name: Checkout repository', \\\n"
        "    '        uses: actions/checkout@v6', \\\n"
        "    '      - name: Set up Python', \\\n"
        "    '        uses: actions/setup-python@v6', \\\n"
        "    '        with:', \\\n"
        "    ('          python-version: \"' + $pythonVersion + '\"'), \\\n"
        "    '      - name: Set up uv', \\\n"
        "    '        uses: astral-sh/setup-uv@v7', \\\n"
        "    '      - name: Install check tooling', \\\n"
        "    '        run: |', \\\n"
        "    '          python -m pip install --upgrade pip', \\\n"
        "    '          python -m pip install twine', \\\n"
        "    '      - name: Build sdist and wheel', \\\n"
        "    '        run: uv build --no-sources', \\\n"
        "    '      - name: Check distributions', \\\n"
        "    '        run: python -m twine check dist/*', \\\n"
        "    '      - name: Upload distributions artifact', \\\n"
        "    '        uses: actions/upload-artifact@v7', \\\n"
        "    '        with:', \\\n"
        "    '          name: python-distributions', \\\n"
        "    '          path: dist/', \\\n"
        "    '  publish:', \\\n"
        "    '    name: Publish to PyPI', \\\n"
        "    '    needs: build', \\\n"
        "    '    runs-on: ubuntu-latest', \\\n"
        "    '    environment:', \\\n"
        "    '      name: pypi', \\\n"
        "    '    permissions:', \\\n"
        "    '      contents: read', \\\n"
        "    '      id-token: write', \\\n"
        "    '    steps:', \\\n"
        "    '      - name: Download distributions artifact', \\\n"
        "    '        uses: actions/download-artifact@v8', \\\n"
        "    '        with:', \\\n"
        "    '          name: python-distributions', \\\n"
        "    '          path: dist/', \\\n"
        "    '      - name: Set up uv', \\\n"
        "    '        uses: astral-sh/setup-uv@v7', \\\n"
        "    '      - name: Publish package to PyPI', \\\n"
        "    '        run: uv publish --trusted-publishing always --check-url https://pypi.org/simple dist/*' \\\n"
        "    ); \\\n"
        "    $qualityLines = @( \\\n"
        "    'name: Quality and Security', \\\n"
        "    '\"on\":', \\\n"
        "    '  pull_request:', \\\n"
        "    '  push:', \\\n"
        "    '    branches: [main]', \\\n"
        "    '  workflow_dispatch:', \\\n"
        "    'permissions:', \\\n"
        "    '  contents: read', \\\n"
        "    'jobs:', \\\n"
        "    '  quality-security:', \\\n"
        "    '    name: Quality and security checks', \\\n"
        "    '    runs-on: ubuntu-latest', \\\n"
        "    '    timeout-minutes: 20', \\\n"
        "    '    steps:', \\\n"
        "    '      - name: Checkout repository', \\\n"
        "    '        uses: actions/checkout@v6', \\\n"
        "    '      - name: Set up Python', \\\n"
        "    '        uses: actions/setup-python@v6', \\\n"
        "    '        with:', \\\n"
        "    ('          python-version: \"' + $pythonVersion + '\"'), \\\n"
        "    '      - name: Set up uv', \\\n"
        "    '        uses: astral-sh/setup-uv@v7', \\\n"
        "    '      - name: Install project with dev dependencies', \\\n"
        "    '        run: uv sync --extra dev', \\\n"
        "    '      - name: Run quality and security hooks', \\\n"
        "    '        run: uv run prek run vulture deptry detect-secrets --all-files' \\\n"
        "    ); \\\n"
        "    $testsLines = @( \\\n"
        "    'name: Tests', \\\n"
        "    '\"on\":', \\\n"
        "    '  pull_request:', \\\n"
        "    '  push:', \\\n"
        "    '    branches: [main]', \\\n"
        "    '  workflow_dispatch:', \\\n"
        "    'permissions:', \\\n"
        "    '  contents: read', \\\n"
        "    'jobs:', \\\n"
        "    '  tests:', \\\n"
        "    '    name: Test suite with coverage', \\\n"
        "    '    runs-on: ubuntu-latest', \\\n"
        "    '    timeout-minutes: 20', \\\n"
        "    '    steps:', \\\n"
        "    '      - name: Checkout repository', \\\n"
        "    '        uses: actions/checkout@v6', \\\n"
        "    '      - name: Set up Python', \\\n"
        "    '        uses: actions/setup-python@v6', \\\n"
        "    '        with:', \\\n"
        "    ('          python-version: \"' + $pythonVersion + '\"'), \\\n"
        "    '      - name: Set up uv', \\\n"
        "    '        uses: astral-sh/setup-uv@v7', \\\n"
        "    '      - name: Install project with dev dependencies', \\\n"
        "    '        run: uv sync --extra dev', \\\n"
        "    '      - name: Run coverage gate hook', \\\n"
        "    '        run: uv run prek run coverage-100 --all-files' \\\n"
        "    ); \\\n"
        "    $typecheckLines = @( \\\n"
        "    'name: Typecheck', \\\n"
        "    '\"on\":', \\\n"
        "    '  pull_request:', \\\n"
        "    '  push:', \\\n"
        "    '    branches: [main]', \\\n"
        "    '  workflow_dispatch:', \\\n"
        "    'permissions:', \\\n"
        "    '  contents: read', \\\n"
        "    'jobs:', \\\n"
        "    '  typecheck:', \\\n"
        "    '    name: Type analysis', \\\n"
        "    '    runs-on: ubuntu-latest', \\\n"
        "    '    timeout-minutes: 20', \\\n"
        "    '    steps:', \\\n"
        "    '      - name: Checkout repository', \\\n"
        "    '        uses: actions/checkout@v6', \\\n"
        "    '      - name: Set up Python', \\\n"
        "    '        uses: actions/setup-python@v6', \\\n"
        "    '        with:', \\\n"
        "    ('          python-version: \"' + $pythonVersion + '\"'), \\\n"
        "    '      - name: Set up uv', \\\n"
        "    '        uses: astral-sh/setup-uv@v7', \\\n"
        "    '      - name: Install project with dev dependencies', \\\n"
        "    '        run: uv sync --extra dev', \\\n"
        "    '      - name: Run type-check hooks', \\\n"
        "    '        run: uv run prek run basedpyright ty-check --all-files' \\\n"
        "    ); \\\n"
        "    $utf8NoBom = New-Object System.Text.UTF8Encoding($false); \\\n"
        "    [System.IO.File]::WriteAllText($dependabotPath, ($dependabotLines -join \"`n\"), $utf8NoBom); \\\n"
        "    [System.IO.File]::WriteAllText($lintFormatPath, ($lintFormatLines -join \"`n\"), $utf8NoBom); \\\n"
        "    [System.IO.File]::WriteAllText($publishPath, ($publishLines -join \"`n\"), $utf8NoBom); \\\n"
        "    [System.IO.File]::WriteAllText($qualityPath, ($qualityLines -join \"`n\"), $utf8NoBom); \\\n"
        "    [System.IO.File]::WriteAllText($testsPath, ($testsLines -join \"`n\"), $utf8NoBom); \\\n"
        "    [System.IO.File]::WriteAllText($typecheckPath, ($typecheckLines -join \"`n\"), $utf8NoBom); \\\n"
        "    Write-Host ('Created GitHub automation files under ' + $targetGithubDir)\n"
    )
    (justfiles_dir / "github_actions.just").write_text(github_actions_just, encoding="utf-8")

    # --- clean.just ---
    clean_just = (
        "clean:\n"
        "    $confirmation = Read-Host 'Are you sure you want to clean this project directory? Type \"delete my stuff\" to continue'; \\\n"
        "    if ($confirmation -ne 'delete my stuff') { throw 'Clean cancelled.' }; \\\n"
        "    $root = (Resolve-Path '.').Path; \\\n"
        "    if (-not (Test-Path (Join-Path $root 'pyproject.toml'))) { throw 'Refusing to clean: run this only from a project root (pyproject.toml required).' }; \\\n"
        "    $items = Get-ChildItem -LiteralPath $root -Force; \\\n"
        "    foreach ($item in $items) { \\\n"
        "        Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction SilentlyContinue; \\\n"
        "    }; \\\n"
        "    Write-Host ('Clean complete for ' + $root + '.')\n"
    )
    (justfiles_dir / "clean.just").write_text(clean_just, encoding="utf-8")

    # --- justfile ---
    justfile_content = (
        'set shell := ["powershell", "-NoProfile", "-Command"]\n'
        "\n"
        "import '.justfiles/prek.just'\n"
        "import '.justfiles/license.just'\n"
        "import '.justfiles/github_actions.just'\n"
        "import '.justfiles/clean.just'\n"
        "\n"
        "_default:\n"
        "    @just --list\n"
        "\n"
        "ruff:\n"
        "    uvx ruff check --exclude typings\n"
        "    uvx ruff format --exclude typings\n"
        "\n"
        "# Run Python type checking with basedpyright.\n"
        "typecheck:\n"
        "    uvx basedpyright\n"
        "\n"
        "# Run prek hooks against all files.\n"
        "prek:\n"
        "    uv run prek run --all-files; uv run prek run --all-files\n"
        "\n"
        "test:\n"
        "    uv run pytest --doctest-modules\n"
        "\n"
        "# Run tests with coverage report.\n"
        "test-cov:\n"
        "    $projectNameMatch = Select-String -Path 'pyproject.toml' -Pattern '^name\\s*=\\s*\"([^\\\"]+)\"'"
        " -AllMatches | Select-Object -First 1;"
        " if (-not $projectNameMatch -or $projectNameMatch.Matches.Count -eq 0) { throw 'project.name not found in pyproject.toml.' };"
        " $packageName = $projectNameMatch.Matches[0].Groups[1].Value -replace '-', '_';"
        " uv run pytest --doctest-modules --cov=('src/' + $packageName) --cov-report=term-missing\n"
    )
    (project_dir / "justfile").write_text(justfile_content, encoding="utf-8")
    print(f"Created justfile and .justfiles/ in {project_dir}")


def setup_prek(project_dir: Path, package_name: str, python_version: str) -> None:
    """Add prek to dev dependencies and write .pre-commit-config.yaml."""
    _run(["uv", "add", "--optional", "dev", "prek"], cwd=project_dir)

    py_ver = python_version  # e.g. "3.14"
    py_flag = f"--py{py_ver.replace('.', '')}-plus"

    lines = [
        "default_language_version:",
        f"  python: python{py_ver}",
        "repos:",
        "  - repo: local",
        "    hooks:",
        "      - id: prek-auto-update",
        "        name: prek-auto-update",
        "        entry: uv run prek auto-update",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "        fail_fast: true",
        "  - repo: https://github.com/bwhmather/ssort",
        "    rev: 0.16.0",
        "    hooks:",
        "      - id: ssort",
        "  - repo: https://github.com/pre-commit/pre-commit-hooks",
        "    rev: v6.0.0",
        "    hooks:",
        "      - id: fix-byte-order-marker",
        "      - id: check-merge-conflict",
        "      - id: end-of-file-fixer",
        r"        exclude: ^static/.*\.svg$",
        "      - id: trailing-whitespace",
        "      - id: mixed-line-ending",
        r"        exclude: ^static/.*\.svg$",
        "      - id: check-yaml",
        "      - id: check-toml",
        "      - id: check-added-large-files",
        r"        exclude: ^tests/media/.*\.cbz$",
        "      - id: debug-statements",
        f"        language_version: python{py_ver}",
        "      - id: check-executables-have-shebangs",
        "      - id: check-shebang-scripts-are-executable",
        "  - repo: https://github.com/google/yamlfmt",
        "    rev: v0.21.0",
        "    hooks:",
        "      - id: yamlfmt",
        r"        files: \.(yml|yaml)$",
        "  - repo: https://github.com/adrienverge/yamllint",
        "    rev: v1.38.0",
        "    hooks:",
        "      - id: yamllint",
        r"        files: \.(yml|yaml)$",
        "  - repo: https://github.com/shellcheck-py/shellcheck-py",
        "    rev: v0.11.0.1",
        "    hooks:",
        "      - id: shellcheck",
        "  - repo: https://github.com/scop/pre-commit-shfmt",
        "    rev: v3.13.1-1",
        "    hooks:",
        "      - id: shfmt",
        "  - repo: https://github.com/crate-ci/typos",
        "    rev: v1.45.0",
        "    hooks:",
        "      - id: typos",
        "  - repo: https://github.com/executablebooks/mdformat",
        "    rev: 1.0.0",
        "    hooks:",
        "      - id: mdformat",
        r"        files: \.md$",
        "  - repo: https://github.com/DavidAnson/markdownlint-cli2",
        "    rev: v0.22.0",
        "    hooks:",
        "      - id: markdownlint-cli2",
        "  - repo: https://github.com/ComPWA/taplo-pre-commit",
        "    # toml formatter",
        "",
        "    rev: v0.9.3",
        "    hooks:",
        "      - id: taplo-format",
        "      - id: taplo-lint",
        "  - repo: https://github.com/asottile/pyupgrade",
        "    rev: v3.21.2",
        "    hooks:",
        "      - id: pyupgrade",
        f"        language_version: python{py_ver}",
        f"        args: [{py_flag}, --keep-runtime-typing]",
        r"        files: ^(src|tests)/.*\.py$",
        "  - repo: https://github.com/hadialqattan/pycln",
        "    rev: v2.6.0",
        "    hooks:",
        "      - id: pycln",
        f"        language_version: python{py_ver}",
        "        args: [src, tests]",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "  - repo: https://github.com/astral-sh/ruff-pre-commit",
        "    rev: v0.15.10",
        "    hooks:",
        "      - id: ruff-check",
        f"        language_version: python{py_ver}",
        "        args: [--fix, --exclude, typings]",
        r"        files: ^(src|tests)/.*\.py$",
        "      - id: ruff-format",
        f"        language_version: python{py_ver}",
        "        args: [--exclude, typings]",
        r"        files: ^(src|tests)/.*\.py$",
        "      - id: ruff-check",
        "        name: ruff-check-post-format",
        f"        language_version: python{py_ver}",
        "        args: [--exclude, typings]",
        r"        files: ^(src|tests)/.*\.py$",
        "  - repo: local",
        "    hooks:",
        "      - id: autopep695-format",
        "        name: autopep695-format",
        "        entry: uvx autopep695 format",
        "        language: system",
        r"        files: ^(src|tests)/.*\.py$",
        "        stages: [pre-commit]",
        "      - id: vulture",
        "        name: vulture",
        "        entry: |",
        f"          uvx --python {py_ver} vulture src --min-confidence 80 --ignore-names",
        "          dst,secure,httponly,samesite,unc_path,package_family_name,logo44x44",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "      - id: deptry",
        "        name: deptry",
        "        entry: uvx deptry . --ignore DEP001,DEP002",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "      - id: refurb",
        "        name: refurb",
        "        entry: uvx ruff check --select FURB --ignore FURB110 src tests",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "      - id: basedpyright",
        "        name: basedpyright",
        "        entry: uvx basedpyright",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "      - id: ty-check",
        "        name: ty-check",
        "        entry: uvx ty check",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "      - id: pip-audit",
        "        name: pip-audit",
        "        entry: uvx pip-audit",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "      - id: coverage-100",
        "        name: coverage-100",
        f"        entry: uv run pytest --doctest-modules --cov=src/{package_name} --cov-report=term-missing --cov-fail-under=100 src/{package_name}",
        "        language: system",
        "        pass_filenames: false",
        "        always_run: true",
        "        stages: [pre-commit]",
        "  - repo: https://github.com/Yelp/detect-secrets",
        "    rev: v1.5.0",
        "    hooks:",
        "      - id: detect-secrets",
        f"        language_version: python{py_ver}",
        '        args: ["--baseline", ".secrets.baseline"]',
        "        stages: [pre-commit]",
    ]

    pre_commit_yaml = "\n".join(lines) + "\n"
    (project_dir / ".pre-commit-config.yaml").write_text(pre_commit_yaml, encoding="utf-8")
    print(f"Created .pre-commit-config.yaml in {project_dir}")
    _run(["uv", "run", "prek", "install"], cwd=project_dir)


def setup_github_actions(project_dir: Path, python_version: str) -> None:
    """Create .github/dependabot.yml and workflow YAML files."""
    github_dir = project_dir / ".github"
    workflows_dir = github_dir / "workflows"
    github_dir.mkdir(exist_ok=True)
    workflows_dir.mkdir(exist_ok=True)

    pv = python_version

    dependabot = "\n".join([
        "version: 2",
        "updates:",
        '  - package-ecosystem: "github-actions"',
        '    directory: "/"',
        "    schedule:",
        '      interval: "weekly"',
        "    open-pull-requests-limit: 10",
        '  - package-ecosystem: "uv"',
        '    directory: "/"',
        "    schedule:",
        '      interval: "weekly"',
        "    open-pull-requests-limit: 10",
    ]) + "\n"

    lint_format = "\n".join([
        "name: Lint and Format",
        '"on":',
        "  pull_request:",
        "  push:",
        "    branches: [main]",
        "  workflow_dispatch:",
        "permissions:",
        "  contents: read",
        "jobs:",
        "  lint-format:",
        "    name: Lint and format checks",
        "    runs-on: ubuntu-latest",
        "    timeout-minutes: 30",
        "    steps:",
        "      - name: Checkout repository",
        "        uses: actions/checkout@v6",
        "      - name: Set up Python",
        "        uses: actions/setup-python@v6",
        "        with:",
        f'          python-version: "{pv}"',
        "      - name: Set up uv",
        "        uses: astral-sh/setup-uv@v7",
        "      - name: Install project with dev dependencies",
        "        run: uv sync --extra dev",
        "      - name: Run lint and format hooks",
        "        run: |",
        "          uv run prek run ssort --all-files",
        "          uv run prek run fix-byte-order-marker check-merge-conflict \\",
        "            end-of-file-fixer trailing-whitespace mixed-line-ending --all-files",
        "          uv run prek run check-yaml check-toml check-added-large-files \\",
        "            check-executables-have-shebangs \\",
        "            check-shebang-scripts-are-executable \\",
        "            --all-files",
        "          uv run prek run yamlfmt yamllint --all-files",
        "          uv run prek run typos mdformat markdownlint-cli2 --all-files",
        "          uv run prek run taplo-format taplo-lint --all-files",
        "          uv run prek run pyupgrade pycln autopep695-format --all-files",
        "          uv run prek run ruff-check ruff-format ruff-check-post-format \\",
        "            refurb --all-files",
    ]) + "\n"

    publish = "\n".join([
        "name: Publish to PyPI",
        '"on":',
        "  release:",
        "    types: [published]",
        "  workflow_dispatch:",
        "permissions:",
        "  contents: read",
        "jobs:",
        "  build:",
        "    name: Build distributions",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - name: Checkout repository",
        "        uses: actions/checkout@v6",
        "      - name: Set up Python",
        "        uses: actions/setup-python@v6",
        "        with:",
        f'          python-version: "{pv}"',
        "      - name: Set up uv",
        "        uses: astral-sh/setup-uv@v7",
        "      - name: Install check tooling",
        "        run: |",
        "          python -m pip install --upgrade pip",
        "          python -m pip install twine",
        "      - name: Build sdist and wheel",
        "        run: uv build --no-sources",
        "      - name: Check distributions",
        "        run: python -m twine check dist/*",
        "      - name: Upload distributions artifact",
        "        uses: actions/upload-artifact@v7",
        "        with:",
        "          name: python-distributions",
        "          path: dist/",
        "  publish:",
        "    name: Publish to PyPI",
        "    needs: build",
        "    runs-on: ubuntu-latest",
        "    environment:",
        "      name: pypi",
        "    permissions:",
        "      contents: read",
        "      id-token: write",
        "    steps:",
        "      - name: Download distributions artifact",
        "        uses: actions/download-artifact@v8",
        "        with:",
        "          name: python-distributions",
        "          path: dist/",
        "      - name: Set up uv",
        "        uses: astral-sh/setup-uv@v7",
        "      - name: Publish package to PyPI",
        "        run: uv publish --trusted-publishing always --check-url https://pypi.org/simple dist/*",
    ]) + "\n"

    quality = "\n".join([
        "name: Quality and Security",
        '"on":',
        "  pull_request:",
        "  push:",
        "    branches: [main]",
        "  workflow_dispatch:",
        "permissions:",
        "  contents: read",
        "jobs:",
        "  quality-security:",
        "    name: Quality and security checks",
        "    runs-on: ubuntu-latest",
        "    timeout-minutes: 20",
        "    steps:",
        "      - name: Checkout repository",
        "        uses: actions/checkout@v6",
        "      - name: Set up Python",
        "        uses: actions/setup-python@v6",
        "        with:",
        f'          python-version: "{pv}"',
        "      - name: Set up uv",
        "        uses: astral-sh/setup-uv@v7",
        "      - name: Install project with dev dependencies",
        "        run: uv sync --extra dev",
        "      - name: Run quality and security hooks",
        "        run: uv run prek run vulture deptry detect-secrets --all-files",
    ]) + "\n"

    tests = "\n".join([
        "name: Tests",
        '"on":',
        "  pull_request:",
        "  push:",
        "    branches: [main]",
        "  workflow_dispatch:",
        "permissions:",
        "  contents: read",
        "jobs:",
        "  tests:",
        "    name: Test suite with coverage",
        "    runs-on: ubuntu-latest",
        "    timeout-minutes: 20",
        "    steps:",
        "      - name: Checkout repository",
        "        uses: actions/checkout@v6",
        "      - name: Set up Python",
        "        uses: actions/setup-python@v6",
        "        with:",
        f'          python-version: "{pv}"',
        "      - name: Set up uv",
        "        uses: astral-sh/setup-uv@v7",
        "      - name: Install project with dev dependencies",
        "        run: uv sync --extra dev",
        "      - name: Run coverage gate hook",
        "        run: uv run prek run coverage-100 --all-files",
    ]) + "\n"

    typecheck = "\n".join([
        "name: Typecheck",
        '"on":',
        "  pull_request:",
        "  push:",
        "    branches: [main]",
        "  workflow_dispatch:",
        "permissions:",
        "  contents: read",
        "jobs:",
        "  typecheck:",
        "    name: Type analysis",
        "    runs-on: ubuntu-latest",
        "    timeout-minutes: 20",
        "    steps:",
        "      - name: Checkout repository",
        "        uses: actions/checkout@v6",
        "      - name: Set up Python",
        "        uses: actions/setup-python@v6",
        "        with:",
        f'          python-version: "{pv}"',
        "      - name: Set up uv",
        "        uses: astral-sh/setup-uv@v7",
        "      - name: Install project with dev dependencies",
        "        run: uv sync --extra dev",
        "      - name: Run type-check hooks",
        "        run: uv run prek run basedpyright ty-check --all-files",
    ]) + "\n"

    (github_dir / "dependabot.yml").write_text(dependabot, encoding="utf-8")
    (workflows_dir / "lint-format.yml").write_text(lint_format, encoding="utf-8")
    (workflows_dir / "publish-pypi.yml").write_text(publish, encoding="utf-8")
    (workflows_dir / "quality-security.yml").write_text(quality, encoding="utf-8")
    (workflows_dir / "tests.yml").write_text(tests, encoding="utf-8")
    (workflows_dir / "typecheck.yml").write_text(typecheck, encoding="utf-8")
    print(f"Created GitHub automation files under {github_dir}")


def _get_license_classifier(spdx_key: str) -> str:
    """Return the PyPI trove classifier for a given SPDX license key."""
    return _LICENSE_CLASSIFIERS.get(spdx_key, "License :: Other/Proprietary License")


def _update_pyproject_license(project_dir: Path, spdx_name: str, python_version: str) -> None:
    """Patch the license field and classifiers in an existing pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        print("pyproject.toml not found, skipping pyproject license update.")
        return

    content = pyproject.read_text(encoding="utf-8")
    license_line = f'license = "{spdx_name}"'
    license_classifier = _get_license_classifier(spdx_name)
    py_ver = python_version

    # Update license field
    if re.search(r"(?m)^license\s*=", content):
        content = re.sub(r"(?m)^license\s*=.*$", license_line, content, count=1)
    else:
        content = re.sub(r"(?m)^readme\s*=.*$", r"\g<0>\n" + license_line, content, count=1)
        if license_line not in content:
            content = content.rstrip() + "\n" + license_line + "\n"

    classifiers_block = "\n".join([
        "classifiers = [",
        f'  "{license_classifier}",',
        '  "Operating System :: Microsoft :: Windows",',
        '  "Programming Language :: Python :: 3",',
        f'  "Programming Language :: Python :: {py_ver}",',
        "]",
    ])

    if re.search(r"(?ms)^classifiers\s*=\s*\[.*?^\]", content):
        content = re.sub(r"(?ms)^classifiers\s*=\s*\[.*?^\]", classifiers_block, content, count=1)
    else:
        content = re.sub(r"(?m)^requires-python\s*=.*$", r"\g<0>\n" + classifiers_block, content, count=1)
        if classifiers_block not in content:
            content = content.rstrip() + "\n" + classifiers_block + "\n"

    pyproject.write_text(content, encoding="utf-8")
    print(f"Updated {pyproject} license/classifiers for {spdx_name}")


def pick_license(project_dir: Path, python_version: str) -> None:
    """Interactively fetch, filter, and download a license from scancode-licensedb."""
    print("Fetching license index from scancode-licensedb...")
    try:
        with urllib.request.urlopen(_SCANCODE_INDEX_URL, timeout=30) as resp:  # noqa: S310
            all_licenses: list[dict[str, object]] = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not fetch license index: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    licenses = [
        lic
        for lic in all_licenses
        if not lic.get("is_exception") and not lic.get("is_deprecated") and lic.get("license")
    ]
    licenses.sort(key=lambda x: (str(x.get("spdx_license_key", "")), str(x.get("license_key", ""))))

    if not licenses:
        print("error: no licenses found in remote index.", file=sys.stderr)
        raise SystemExit(1)

    print(f"Found {len(licenses)} licenses.")
    query = input("Filter licenses by text (blank for all): ").strip()
    if query:
        filtered = [
            lic
            for lic in licenses
            if query.lower() in str(lic.get("spdx_license_key", "")).lower()
            or query.lower() in str(lic.get("license_key", "")).lower()
        ]
        if not filtered:
            print(f"error: no licenses matched filter: {query}", file=sys.stderr)
            raise SystemExit(1)
        licenses = filtered

    print(f"Showing {len(licenses)} licenses.")
    for i, lic in enumerate(licenses, 1):
        name = lic.get("spdx_license_key") or lic.get("license_key", "")
        print(f"{i}. {name}")

    selection_str = input("Enter number: ").strip()
    try:
        selection = int(selection_str)
    except ValueError:
        print("error: invalid selection.", file=sys.stderr)
        raise SystemExit(1)

    if selection < 1 or selection > len(licenses):
        print("error: selection out of range.", file=sys.stderr)
        raise SystemExit(1)

    chosen = licenses[selection - 1]
    file_name = str(chosen["license"])
    url = _SCANCODE_BASE_URL + file_name
    spdx_name = str(chosen.get("spdx_license_key") or chosen.get("license_key", file_name))

    print(f"Downloading {spdx_name}...")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            license_text = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not download license: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    (project_dir / "LICENSE").write_text(license_text, encoding="utf-8")
    print(f"Downloaded {spdx_name} to {project_dir / 'LICENSE'}")
    _update_pyproject_license(project_dir, spdx_name, python_version)
