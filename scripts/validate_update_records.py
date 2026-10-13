#!/usr/bin/env python3
"""Validate newly added package version records."""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

from check_package_updates import SHA256_RE, classify_arch


RECORD_RE = re.compile(r"^pkg/pkginfo_(arm64|amd64)/([^/]+)/_([^@]+)@(.+)$")


def validate(path: Path) -> list[str]:
    relative = path.as_posix()
    match = RECORD_RE.fullmatch(relative)
    if match is None:
        return [f"{relative}: not a package version record"]

    arch, directory_name, record_name, version = match.groups()
    errors: list[str] = []
    if directory_name != record_name:
        errors.append(f"{relative}: package directory and record name do not match")
    if not version:
        errors.append(f"{relative}: empty version")

    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        field = re.match(r'^([A-Za-z_][A-Za-z_0-9]*):\s*"([^"]*)"\s*$', line)
        if field:
            fields[field.group(1)] = field.group(2)
    digest = fields.get("sha256", "")
    if not SHA256_RE.fullmatch(digest):
        errors.append(f"{relative}: sha256 must be 64 lowercase hexadecimal characters")
    url = fields.get("url", "")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        errors.append(f"{relative}: URL must be HTTPS")
    elif classify_arch(Path(urllib.parse.unquote(parsed.path)).name) != arch:
        errors.append(f"{relative}: URL filename does not identify the {arch} architecture")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate_update_records.py <new-record> [...]", file=sys.stderr)
        return 2
    errors = [error for arg in sys.argv[1:] for error in validate(Path(arg))]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {len(sys.argv) - 1} new package version record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
