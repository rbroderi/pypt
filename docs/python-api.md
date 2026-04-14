# Python API

Full API reference is available in the generated
[Sphinx API docs](api/apidoc/modules.html).

Use a simple import path for quick tasks, or construct richer workflows in code.

## One-liner

```python
from pyptmpl import __version__

print(__version__)
```

## Advanced

```python
from importlib import import_module

pkg = import_module("pyptmpl")
print(pkg.__name__)
```
