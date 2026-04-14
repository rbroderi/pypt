import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _project_dir(base_dir: Path, project_name: str) -> Path:
    for candidate in (project_name, project_name.replace("-", "_")):
        path = base_dir / candidate
        if path.is_dir():
            return path
    raise AssertionError(f"project directory not found for {project_name!r}")


def test_pypt_cli_subprocess_generates_expected_project(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is required for integration scaffolding test")

    project_name = "integration-demo"
    package_name = project_name.replace("-", "_")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    description = "integration test project"

    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    src_path = str(repo_root / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else src_path + os.pathsep + existing_pythonpath

    cmd = [
        sys.executable,
        "-m",
        "pyptmpl",
        project_name,
        "--python-version",
        python_version,
        "--description",
        description,
        "--no-license",
        "--no-prek",
        "--no-github-actions",
        "--no-sync",
    ]

    result = subprocess.run(
        cmd,
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, f"pyptmpl subprocess failed\nstdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"

    project_dir = _project_dir(tmp_path, project_name)

    expected_files = [
        project_dir / "pyproject.toml",
        project_dir / ".gitignore",
        project_dir / ".yamllint",
        project_dir / ".vscode" / "settings.json",
        project_dir / "justfile",
        project_dir / "docs" / "index.md",
        project_dir / "docs" / "python-api.md",
        project_dir / "docs_sphinx" / "conf.py",
        project_dir / "zensical.toml",
        project_dir / "build.spec",
        project_dir / "src" / package_name / "tests" / "test_smoke.py",
    ]

    for path in expected_files:
        assert path.exists(), f"expected generated file to exist: {path}"

    pyproject = (project_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert f'name = "{project_name}"' in pyproject
    assert f'description = "{description}"' in pyproject
    assert f'requires-python = ">={python_version}"' in pyproject
    assert f'{project_name} = "{package_name}.__main__:main"' in pyproject
    assert "sphinx-autobuild" in pyproject

    smoke_test = (project_dir / "src" / package_name / "tests" / "test_smoke.py").read_text(encoding="utf-8")
    assert f'importlib.import_module("{package_name}")' in smoke_test

    docs_conf = (project_dir / "docs_sphinx" / "conf.py").read_text(encoding="utf-8")
    assert f'project = "{package_name}"' in docs_conf

    build_spec = (project_dir / "build.spec").read_text(encoding="utf-8")
    assert f'"src/{package_name}/__main__.py"' in build_spec

    justfile = (project_dir / "justfile").read_text(encoding="utf-8")
    assert "docs-build:" in justfile
    assert "build:" in justfile
    assert "prek-init:" not in justfile
    assert "github-actions-init:" not in justfile
    assert "license:" not in justfile

    assert not (project_dir / ".pre-commit-config.yaml").exists()
    assert not (project_dir / ".github").exists()
    assert not (project_dir / ".justfiles").exists()
    assert not (project_dir / "uv.lock").exists()


def test_pypt_cli_subprocess_full_flow_with_network(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is required for integration scaffolding test")

    project_name = "integration-full"
    package_name = project_name.replace("-", "_")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    description = "integration full flow"

    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    src_path = str(repo_root / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else src_path + os.pathsep + existing_pythonpath

    cmd = [
        sys.executable,
        "-m",
        "pyptmpl",
        project_name,
        "--python-version",
        python_version,
        "--description",
        description,
    ]

    # pick_license prompts twice: filter query and selection index
    result = subprocess.run(
        cmd,
        cwd=tmp_path,
        env=env,
        text=True,
        input="\n1\n",
        capture_output=True,
        check=False,
        timeout=600,
    )

    assert result.returncode == 0, f"pyptmpl subprocess failed\nstdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"

    project_dir = _project_dir(tmp_path, project_name)
    expected = [
        project_dir / "LICENSE",
        project_dir / ".pre-commit-config.yaml",
        project_dir / ".secrets.baseline",
        project_dir / "uv.lock",
        project_dir / ".github" / "dependabot.yml",
        project_dir / ".github" / "workflows" / "docs.yml",
        project_dir / ".github" / "workflows" / "tests.yml",
        project_dir / ".github" / "workflows" / "typecheck.yml",
        project_dir / ".github" / "workflows" / "quality-security.yml",
        project_dir / ".github" / "workflows" / "lint-format.yml",
        project_dir / ".github" / "workflows" / "publish-pypi.yml",
        project_dir / ".github" / "workflows" / "github-release.yml",
        project_dir / ".github" / "workflows" / "sphinx-api.yml",
        project_dir / "src" / package_name / "tests" / "test_smoke.py",
    ]
    for path in expected:
        assert path.exists(), f"expected generated file to exist: {path}"

    assert (project_dir / "LICENSE").read_text(encoding="utf-8").strip() != ""

    pyproject = (project_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert f'name = "{project_name}"' in pyproject
    assert f'requires-python = ">={python_version}"' in pyproject
    assert f'{project_name} = "{package_name}.__main__:main"' in pyproject
    assert "docs = [" in pyproject
    assert "build = [" in pyproject
