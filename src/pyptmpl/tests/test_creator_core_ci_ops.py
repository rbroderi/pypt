# pyright: reportPrivateLocalImportUsage=false,reportUnknownLambdaType=false,reportUnusedParameter=false,reportUnannotatedClassAttribute=false

from pathlib import Path

from pyptmpl.creator_core import ci_ops
from pyptmpl.creator_core import templates
from pyptmpl.tests._helpers import CommandRecorder


def test_setup_prek(tmp_path: Path) -> None:
    recorder = CommandRecorder()

    def fake_load(path: str) -> str:
        if path == "pre-commit-config.yaml.tmpl":
            return "py={{python_version}} flag={{py_flag}} pkg={{package_name}}"
        if path == ".secrets.baseline.tmpl":
            return '{"version":"1.5.0","results":{}}'
        raise AssertionError(path)

    ci_ops.setup_prek(
        tmp_path,
        "pkg",
        "3.13",
        run_fn=recorder,
        load_template=fake_load,
        render_template=templates.render_template,
    )

    assert recorder.calls[0] == ["uv", "add", "--optional", "dev", "prek"]
    assert recorder.calls[1] == ["uv", "run", "prek", "install"]
    text = (tmp_path / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "py=3.13" in text
    assert "--py313-plus" in text
    assert "pkg=pkg" in text
    assert (tmp_path / ".secrets.baseline").exists()


def test_setup_github_actions(tmp_path: Path) -> None:
    ci_ops.setup_github_actions(
        tmp_path,
        "3.13",
        load_template=lambda _: "x={{python_version}}",
        render_template=templates.render_template,
    )
    assert (tmp_path / ".github" / "dependabot.yml").exists()
    tests_workflow = (tmp_path / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    docs_workflow = (tmp_path / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "3.13" in tests_workflow
    assert "3.13" in docs_workflow
