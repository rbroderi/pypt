from pathlib import Path
from typing import Self


class FakeResponse:
    def __init__(self, body: str) -> None:
        self._body: bytes = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class CommandRecorder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], cwd: Path | None = None) -> None:
        del cwd
        self.calls.append(cmd)
