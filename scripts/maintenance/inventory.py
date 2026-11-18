#!/usr/bin/env python3
"""Read-only verification of relocated original assets against their manifest."""

import hashlib
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    try:
        manifest = json.loads((root / "docs/source-map.json").read_text())
        assets = manifest["assets"]
        if not isinstance(assets, list):
            raise ValueError("invalid assets")
        checked = missing = mismatched = invalid = 0
        seen_old, seen_new = set(), set()
        for asset in assets:
            try:
                old, new = asset["old"], asset["new"]
                destination = (root / new).resolve()
                if (
                    not isinstance(old, str)
                    or not old
                    or Path(old).is_absolute()
                    or ".." in Path(old).parts
                    or Path(new).is_absolute()
                    or not destination.is_relative_to(root)
                    or old in seen_old
                    or new in seen_new
                    or not isinstance(asset["size"], int)
                    or asset["size"] < 0
                    or not isinstance(asset["role"], str)
                    or not asset["role"]
                    or len(asset["sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in asset["sha256"])
                ):
                    raise ValueError("invalid entry")
                seen_old.add(old)
                seen_new.add(new)
                if not destination.is_file():
                    missing += 1
                    continue
                digest = hashlib.sha256()
                size = 0
                with destination.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                        size += len(chunk)
                if size != asset["size"] or digest.hexdigest() != asset["sha256"]:
                    mismatched += 1
                else:
                    checked += 1
            except (KeyError, TypeError, ValueError, OSError):
                invalid += 1
        print(
            f"Assets: {len(assets)}; verified: {checked}; missing: {missing}; "
            f"mismatched: {mismatched}; invalid: {invalid}"
        )
        return int(bool(missing or mismatched or invalid))
    except (OSError, ValueError, KeyError, TypeError):
        print("Inventory failed: manifest unavailable or invalid.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
