# pyright: reportPrivateUsage=false,reportUnknownLambdaType=false,reportUnusedParameter=false,reportUnannotatedClassAttribute=false
import argparse
import importlib.metadata
import urllib.request
from pathlib import Path

import pytest

from pyptmpl import __main__
from pyptmpl.creator_core import ci_ops
from pyptmpl.creator_core import license_ops
from pyptmpl.creator_core import project_ops
from pyptmpl.creator_core import templates
from pyptmpl.creator_core.project_ops import GitAuthor


def test_prompt_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "  abc  ")


def test_prompt_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "   ")
    with pytest.raises(SystemExit):
        __main__._prompt("x")


def test_main_happy_path_all_features(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = argparse.Namespace(
        project_name="demo-proj",
        python_version="3.13",
        description="desc",
        no_license=False,
        no_prek=False,
        no_github_actions=False,
        no_sync=False,
        github_actions_init=False,
        project_dir=".",
    )

    calls: list[str] = []

    monkeypatch.setattr(
        __main__,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: args})(),
    )
    monkeypatch.setattr(__main__, "check_uv", lambda: calls.append("check_uv"))
    monkeypatch.setattr(__main__, "get_git_author", lambda: type("A", (), {"name": "n", "email": "e"})())
    monkeypatch.setattr(__main__, "init_project", lambda n, p, c: tmp_path / "demo-proj")
    monkeypatch.setattr(__main__, "write_pyproject", lambda *a, **k: calls.append("write_pyproject"))
    monkeypatch.setattr(__main__, "create_smoke_test", lambda *a, **k: calls.append("create_smoke_test"))
    monkeypatch.setattr(__main__, "create_venv", lambda *a, **k: calls.append("create_venv"))
    monkeypatch.setattr(__main__, "setup_gitignore", lambda *a, **k: calls.append("setup_gitignore"))
    monkeypatch.setattr(__main__, "setup_yamllint", lambda *a, **k: calls.append("setup_yamllint"))
    monkeypatch.setattr(__main__, "setup_vscode", lambda *a, **k: calls.append("setup_vscode"))
    monkeypatch.setattr(__main__, "setup_justfiles", lambda *a, **k: calls.append("setup_justfiles"))
    monkeypatch.setattr(
        __main__,
        "setup_docs_build_assets",
        lambda *a, **k: calls.append("setup_docs_build_assets"),
    )
    monkeypatch.setattr(__main__, "pick_license", lambda *a, **k: calls.append("pick_license"))
    monkeypatch.setattr(__main__, "setup_prek", lambda *a, **k: calls.append("setup_prek"))
    monkeypatch.setattr(
        __main__,
        "setup_github_actions",
        lambda *a, **k: calls.append("setup_github_actions"),
    )
    monkeypatch.setattr(__main__, "sync_project", lambda *a, **k: calls.append("sync_project"))

    rc = __main__.main()
    out = capsys.readouterr().out

    assert rc == __main__.OK
    assert "Bootstrap complete" in out
    assert "pick_license" in calls
    assert "setup_prek" in calls
    assert "setup_github_actions" in calls
    assert "setup_docs_build_assets" in calls
    assert "sync_project" in calls


def test_main_skips_optional_and_prompts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args = argparse.Namespace(
        project_name=None,
        python_version=None,
        description=None,
        no_license=True,
        no_prek=True,
        no_github_actions=True,
        no_sync=True,
        github_actions_init=False,
        project_dir=".",
    )
    prompts = iter(["proj", "3.13", "desc"])
    seen: list[str] = []

    monkeypatch.setattr(
        __main__,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: args})(),
    )
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))
    monkeypatch.setattr(__main__, "check_uv", lambda: None)
    monkeypatch.setattr(__main__, "get_git_author", lambda: type("A", (), {"name": "n", "email": "e"})())
    monkeypatch.setattr(__main__, "init_project", lambda n, p, c: tmp_path / "proj")
    monkeypatch.setattr(__main__, "write_pyproject", lambda *a, **k: seen.append("write_pyproject"))
    monkeypatch.setattr(__main__, "create_smoke_test", lambda *a, **k: seen.append("create_smoke_test"))
    monkeypatch.setattr(__main__, "create_venv", lambda *a, **k: seen.append("create_venv"))
    monkeypatch.setattr(__main__, "setup_gitignore", lambda *a, **k: seen.append("setup_gitignore"))
    monkeypatch.setattr(__main__, "setup_yamllint", lambda *a, **k: seen.append("setup_yamllint"))
    monkeypatch.setattr(__main__, "setup_vscode", lambda *a, **k: seen.append("setup_vscode"))
    monkeypatch.setattr(__main__, "setup_justfiles", lambda *a, **k: seen.append("setup_justfiles"))
    monkeypatch.setattr(
        __main__,
        "setup_docs_build_assets",
        lambda *a, **k: seen.append("setup_docs_build_assets"),
    )

    def fail(*args, **kwargs):
        raise AssertionError("should not be called")

    monkeypatch.setattr(__main__, "pick_license", fail)
    monkeypatch.setattr(__main__, "setup_prek", fail)
    monkeypatch.setattr(__main__, "setup_github_actions", fail)
    monkeypatch.setattr(__main__, "sync_project", fail)

    rc = __main__.main()
    assert rc == __main__.OK
    assert seen
    assert "setup_docs_build_assets" in seen


def test_build_parser_accepts_flags() -> None:
    parser = __main__._build_parser()
    ns = parser.parse_args(
        [
            "myproj",
            "--python-version",
            "3.13",
            "--description",
            "d",
            "--no-license",
            "--no-prek",
            "--no-github-actions",
            "--no-sync",
        ]
    )
    assert ns.project_name == "myproj"
    assert ns.python_version == "3.13"
    assert ns.description == "d"
    assert ns.no_license is True
    assert ns.no_prek is True
    assert ns.no_github_actions is True
    assert ns.no_sync is True


def test_main_github_actions_init_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args = argparse.Namespace(
        project_name=None,
        python_version=None,
        description=None,
        no_license=False,
        no_prek=False,
        no_github_actions=False,
        no_sync=False,
        github_actions_init=True,
        project_dir=str(tmp_path),
    )
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        __main__,
        "_build_parser",
        lambda: type("P", (), {"parse_args": lambda self: args})(),
    )
    monkeypatch.setattr(__main__, "check_uv", lambda: None)
    monkeypatch.setattr(__main__, "infer_python_version_from_pyproject", lambda p, strict=False: "3.12")
    monkeypatch.setattr(
        __main__,
        "setup_github_actions",
        lambda project_dir, python_version: calls.append((str(project_dir), python_version)),
    )

    rc = __main__.main()
    assert rc == __main__.OK
    assert calls == [(str(tmp_path.resolve()), "3.12")]


def test_fetch_pypi_license_classifiers_success_and_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    __main__._pypi_license_classifiers_cache = None
    calls: list[str] = []

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return b"License :: A\nOther\nLicense :: B\n"

    def fake_urlopen(url: str, timeout: int = 30):
        del timeout
        calls.append(url)
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    first = __main__._fetch_pypi_license_classifiers()
    second = __main__._fetch_pypi_license_classifiers()

    assert first == ["License :: A", "License :: B"]
    assert second == first
    assert len(calls) == 1


def test_fetch_pypi_license_classifiers_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    __main__._pypi_license_classifiers_cache = None

    def fake_urlopen(url: str, timeout: int = 30):
        del url, timeout
        raise OSError("boom")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = __main__._fetch_pypi_license_classifiers()
    err = capsys.readouterr().err

    assert result == []
    assert "could not fetch" in err


def test_main_wrapper_delegates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(templates, "load_template", lambda p: f"tmpl:{p}")
    monkeypatch.setattr(templates, "render_template", lambda t, **k: t + str(k))
    monkeypatch.setattr(project_ops, "run_cmd", lambda cmd, cwd=None: None)
    monkeypatch.setattr(project_ops, "check_uv", lambda: None)
    monkeypatch.setattr(
        project_ops,
        "get_git_author",
        lambda: GitAuthor("n", "e"),
    )
    monkeypatch.setattr(
        project_ops,
        "init_project",
        lambda name, py, cwd, run_fn: cwd / name,
    )

    captured: dict[str, object] = {}

    def fake_write(*args, **kwargs) -> None:
        del kwargs
        captured["write"] = args

    monkeypatch.setattr(project_ops, "write_pyproject", fake_write)
    monkeypatch.setattr(project_ops, "create_smoke_test", lambda *a: None)
    monkeypatch.setattr(project_ops, "create_venv", lambda *a: None)
    monkeypatch.setattr(project_ops, "setup_gitignore", lambda *a: None)
    monkeypatch.setattr(project_ops, "setup_yamllint", lambda *a: None)
    monkeypatch.setattr(project_ops, "setup_vscode", lambda *a: None)
    monkeypatch.setattr(project_ops, "setup_justfiles", lambda *a: None)
    monkeypatch.setattr(project_ops, "setup_docs_build_assets", lambda *a: None)
    monkeypatch.setattr(ci_ops, "setup_prek", lambda *a: None)
    monkeypatch.setattr(ci_ops, "setup_github_actions", lambda *a: None)
    monkeypatch.setattr(
        project_ops,
        "infer_python_version_from_pyproject",
        lambda p, d, strict=False: d,
    )

    assert __main__._load_template("x") == "tmpl:x"
    assert __main__._render("x", y="z") == "x{'y': 'z'}"
    __main__._run(["echo", "x"], tmp_path)
    __main__.check_uv()
    assert __main__.get_git_author() == GitAuthor("n", "e")
    assert __main__.init_project("abc", "3.13", tmp_path) == tmp_path / "abc"
    __main__.write_pyproject(
        tmp_path,
        "proj",
        "pkg",
        "3.13",
        "desc",
        GitAuthor("n", "e"),
    )
    assert "write" in captured


def test_main_wrapper_delegate_tail_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[str] = []
    monkeypatch.setattr(project_ops, "create_smoke_test", lambda *a: seen.append("smoke"))
    monkeypatch.setattr(project_ops, "create_venv", lambda *a: seen.append("venv"))
    monkeypatch.setattr(project_ops, "sync_project", lambda *a: seen.append("sync"))
    monkeypatch.setattr(project_ops, "setup_gitignore", lambda *a: seen.append("gitignore"))
    monkeypatch.setattr(project_ops, "setup_yamllint", lambda *a: seen.append("yamllint"))
    monkeypatch.setattr(project_ops, "setup_vscode", lambda *a: seen.append("vscode"))
    monkeypatch.setattr(project_ops, "setup_justfiles", lambda *a: seen.append("justfiles"))
    monkeypatch.setattr(project_ops, "setup_docs_build_assets", lambda *a: seen.append("docs"))
    monkeypatch.setattr(ci_ops, "setup_prek", lambda *a: seen.append("prek"))
    monkeypatch.setattr(ci_ops, "setup_github_actions", lambda *a: seen.append("gha"))
    monkeypatch.setattr(
        project_ops,
        "infer_python_version_from_pyproject",
        lambda p, d, strict=False: "3.10",
    )

    __main__.create_smoke_test(tmp_path, "pkg")
    __main__.create_venv(tmp_path, "3.13")
    __main__.sync_project(tmp_path)
    __main__.setup_gitignore(tmp_path)
    __main__.setup_yamllint(tmp_path)
    __main__.setup_vscode(tmp_path)
    __main__.setup_justfiles(tmp_path, "pkg")
    __main__.setup_docs_build_assets(tmp_path, "pkg")
    __main__.setup_prek(tmp_path, "pkg", "3.13")
    __main__.setup_github_actions(tmp_path, "3.13")
    assert __main__.infer_python_version_from_pyproject(tmp_path, strict=True) == "3.10"

    assert set(seen) == {
        "smoke",
        "venv",
        "sync",
        "gitignore",
        "yamllint",
        "vscode",
        "justfiles",
        "docs",
        "prek",
        "gha",
    }


def test_main_license_wrapper_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(__main__, "_fetch_pypi_license_classifiers", lambda: ["a"])
    monkeypatch.setattr(license_ops, "match_pypi_classifier", lambda s, c: f"{s}:{c[0]}")
    assert __main__._get_license_classifier("MIT") == "MIT:a"

    seen: dict[str, object] = {}
    monkeypatch.setattr(
        license_ops,
        "update_pyproject_license",
        lambda project_dir, spdx_name, python_version, get_cls: seen.update(
            {
                "project_dir": project_dir,
                "spdx": spdx_name,
                "py": python_version,
                "cls": get_cls("x"),
            }
        ),
    )
    __main__._update_pyproject_license(tmp_path, "MIT", "3.13")
    assert seen["spdx"] == "MIT"

    monkeypatch.setattr(
        license_ops,
        "pick_license",
        lambda *a, **k: (_ for _ in ()).throw(SystemExit(1)),
    )
    with pytest.raises(SystemExit):
        __main__.pick_license(tmp_path, "3.13")
    assert "1" in capsys.readouterr().err


def test_get_version_package_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    __main__.get_version.cache_clear()

    def fail(name: str) -> str:
        del name
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", fail)
    assert __main__.get_version() == "unknown"
