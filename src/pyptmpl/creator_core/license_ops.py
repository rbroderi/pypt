"""License matching, pyproject patching, and interactive license selection."""

import json
import re
from pathlib import Path
from typing import Any
from collections.abc import Callable


def match_pypi_classifier(spdx_key: str, classifiers: list[str]) -> str:
    """Return the best-matching PyPI License :: classifier for an SPDX key."""
    key_lower = spdx_key.lower()
    if key_lower in ("unlicense", "cc0-1.0", "cc0"):
        for cls in classifiers:
            if "public domain" in cls.lower():
                return cls
        return "License :: Other/Proprietary License"

    base_match = re.match(r"^([A-Za-z]+)", spdx_key)
    if not base_match:
        return "License :: Other/Proprietary License"
    base = base_match.group(1).upper()

    version_match = re.search(r"(\d+)(?:\.\d+)?", spdx_key)
    version = version_match.group(1) if version_match else None

    or_later = "or-later" in key_lower or key_lower.endswith("+")

    best_cls = "License :: Other/Proprietary License"
    best_score = -1

    for cls in classifiers:
        abbrev = ""
        m = re.search(r"\(([^)]+)\)", cls)
        if m:
            abbrev = m.group(1).upper()

        score = 0
        if abbrev.startswith(base):
            score += 10
        elif re.search(r"\b" + re.escape(base) + r"\b", cls.upper()):
            score += 3
        elif base in cls.upper():
            score += 1
        else:
            continue

        if version:
            if re.search(r"\bV?" + re.escape(version) + r"\b", cls.upper()):
                score += 5
        elif abbrev and re.search(r"\d", abbrev):
            score -= 8

        if or_later:
            if "or later" in cls.lower():
                score += 3
            else:
                score -= 2
        elif "or later" not in cls.lower():
            score += 1

        if score > best_score:
            best_score = score
            best_cls = cls

    return best_cls


def update_pyproject_license(
    project_dir: Path,
    spdx_name: str,
    python_version: str,
    get_license_classifier: Callable[[str], str],
) -> None:
    """Patch license and classifier block in an existing pyproject.toml."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        print("pyproject.toml not found, skipping pyproject license update.")
        return

    content = pyproject.read_text(encoding="utf-8")
    license_line = f'license = "{spdx_name}"'
    license_classifier = get_license_classifier(spdx_name)
    py_ver = python_version

    if re.search(r"(?m)^license\s*=", content):
        content = re.sub(r"(?m)^license\s*=.*$", license_line, content, count=1)
    else:
        content = re.sub(r"(?m)^readme\s*=.*$", r"\g<0>\n" + license_line, content, count=1)
        if license_line not in content:
            content = content.rstrip() + "\n" + license_line + "\n"

    classifiers_block = "\n".join(
        [
            "classifiers = [",
            f'  "{license_classifier}",',
            '  "Operating System :: OS Independent",',
            '  "Programming Language :: Python :: 3",',
            f'  "Programming Language :: Python :: {py_ver}",',
            "]",
        ]
    )

    if re.search(r"(?ms)^classifiers\s*=\s*\[.*?^\]", content):
        content = re.sub(r"(?ms)^classifiers\s*=\s*\[.*?^\]", classifiers_block, content, count=1)
    else:
        content = re.sub(
            r"(?m)^requires-python\s*=.*$",
            r"\g<0>\n" + classifiers_block,
            content,
            count=1,
        )
        if classifiers_block not in content:
            content = content.rstrip() + "\n" + classifiers_block + "\n"

    pyproject.write_text(content, encoding="utf-8")
    print(f"Updated {pyproject} license/classifiers for {spdx_name}")


def pick_license(
    project_dir: Path,
    python_version: str,
    scancode_index_url: str,
    scancode_base_url: str,
    urlopen: Callable[..., Any],
    update_pyproject_license_fn: Callable[[Path, str, str], None],
) -> None:
    """Interactively fetch, filter, and download a license from scancode-licensedb."""
    print("Fetching license index from scancode-licensedb...")
    try:
        with urlopen(scancode_index_url, timeout=30) as resp:  # noqa: S310
            all_licenses: list[dict[str, object]] = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"error: could not fetch license index: {exc}") from exc

    licenses = [
        lic
        for lic in all_licenses
        if not lic.get("is_exception") and not lic.get("is_deprecated") and lic.get("license")
    ]
    licenses.sort(
        key=lambda x: (
            str(x.get("spdx_license_key", "")),
            str(x.get("license_key", "")),
        )
    )

    if not licenses:
        raise SystemExit("error: no licenses found in remote index.")

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
            raise SystemExit(f"error: no licenses matched filter: {query}")
        licenses = filtered

    print(f"Showing {len(licenses)} licenses.")
    for i, lic in enumerate(licenses, 1):
        name = lic.get("spdx_license_key") or lic.get("license_key", "")
        print(f"{i}. {name}")

    selection_str = input("Enter number: ").strip()
    try:
        selection = int(selection_str)
    except ValueError as exc:
        raise SystemExit("error: invalid selection.") from exc

    if selection < 1 or selection > len(licenses):
        raise SystemExit("error: selection out of range.")

    chosen = licenses[selection - 1]
    file_name = str(chosen["license"])
    base_url = scancode_base_url.rstrip("/") + "/"
    url = base_url + file_name.lstrip("/")
    spdx_name = str(chosen.get("spdx_license_key") or chosen.get("license_key", file_name))

    print(f"Downloading {spdx_name}...")
    try:
        with urlopen(url, timeout=30) as resp:  # noqa: S310
            license_text = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"error: could not download license: {exc}") from exc

    (project_dir / "LICENSE").write_text(license_text, encoding="utf-8")
    print(f"Downloaded {spdx_name} to {project_dir / 'LICENSE'}")
    update_pyproject_license_fn(project_dir, spdx_name, python_version)
