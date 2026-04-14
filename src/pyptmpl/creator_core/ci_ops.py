"""Pre-commit and CI automation setup operations."""

from collections.abc import Callable
from pathlib import Path


def setup_prek(
    project_dir: Path,
    package_name: str,
    python_version: str,
    run_fn: Callable[[list[str], Path | None], None],
    load_template: Callable[[str], str],
    render_template: Callable[..., str],
) -> None:
    """Add prek to dev dependencies and write .pre-commit-config.yaml."""
    run_fn(["uv", "add", "--optional", "dev", "prek"], project_dir)

    py_flag = f"--py{python_version.replace('.', '')}-plus"
    content = render_template(
        load_template("pre-commit-config.yaml.tmpl"),
        python_version=python_version,
        py_flag=py_flag,
        package_name=package_name,
    )
    (project_dir / ".pre-commit-config.yaml").write_text(content, encoding="utf-8")
    print(f"Created .pre-commit-config.yaml in {project_dir}")

    baseline = project_dir / ".secrets.baseline"
    if not baseline.exists():
        baseline.write_text(load_template(".secrets.baseline.tmpl"), encoding="utf-8")
        print(f"Created {baseline}")

    run_fn(["uv", "run", "prek", "install"], project_dir)


def setup_github_actions(
    project_dir: Path,
    python_version: str,
    load_template: Callable[[str], str],
    render_template: Callable[..., str],
) -> None:
    """Create .github/dependabot.yml and workflow YAML files."""
    github_dir = project_dir / ".github"
    workflows_dir = github_dir / "workflows"
    github_dir.mkdir(exist_ok=True)
    workflows_dir.mkdir(exist_ok=True)

    pv = python_version
    (github_dir / "dependabot.yml").write_text(load_template("github/dependabot.yml.tmpl"), encoding="utf-8")
    (workflows_dir / "lint-format.yml").write_text(
        render_template(load_template("github/workflows/lint-format.yml.tmpl"), python_version=pv),
        encoding="utf-8",
    )
    (workflows_dir / "publish-pypi.yml").write_text(
        render_template(load_template("github/workflows/publish-pypi.yml.tmpl"), python_version=pv),
        encoding="utf-8",
    )
    (workflows_dir / "quality-security.yml").write_text(
        render_template(
            load_template("github/workflows/quality-security.yml.tmpl"),
            python_version=pv,
        ),
        encoding="utf-8",
    )
    (workflows_dir / "tests.yml").write_text(
        render_template(load_template("github/workflows/tests.yml.tmpl"), python_version=pv),
        encoding="utf-8",
    )
    (workflows_dir / "typecheck.yml").write_text(
        render_template(load_template("github/workflows/typecheck.yml.tmpl"), python_version=pv),
        encoding="utf-8",
    )
    (workflows_dir / "docs.yml").write_text(
        render_template(load_template("github/workflows/docs.yml.tmpl"), python_version=pv),
        encoding="utf-8",
    )
    (workflows_dir / "github-release.yml").write_text(
        render_template(load_template("github/workflows/github-release.yml.tmpl"), python_version=pv),
        encoding="utf-8",
    )
    (workflows_dir / "sphinx-api.yml").write_text(
        render_template(load_template("github/workflows/sphinx-api.yml.tmpl"), python_version=pv),
        encoding="utf-8",
    )
    print(f"Created GitHub automation files under {github_dir}")
