# pyright: reportPrivateLocalImportUsage=false,reportUnknownLambdaType=false,reportUnusedParameter=false,reportUnannotatedClassAttribute=false

from pyptmpl.creator_core import templates


def test_templates_load_and_render() -> None:
    tmpl = templates.load_template("test_smoke.py.tmpl")
    assert "{{package_name}}" in tmpl
    rendered = templates.render_template("Hello {{name}}", name="world")
    assert rendered == "Hello world"
