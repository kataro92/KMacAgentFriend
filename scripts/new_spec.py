#!/usr/bin/env python3
"""Generate a new spec file from the project template.

Usage:
    python scripts/new_spec.py technical voice-barge-in "Barge-in: stop TTS on speech"
    python scripts/new_spec.py business career-missions "Career missions"

Creates ``specs/<kind>/<TR|BR>-<slug>.md`` with numbered requirement stubs and an
acceptance-criteria block. Refuses to overwrite an existing spec.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SPECS_ROOT = Path(__file__).resolve().parents[1] / "specs"

KIND_PREFIX = {"technical": "TR", "business": "BR"}

TEMPLATE = """# {prefix}-{slug} — {title}

## Purpose

<!-- One or two sentences on why this exists and the user value. -->
TODO: describe the purpose.

## Requirements

**{code}-001** The system SHALL TODO.

**{code}-002** The system SHALL TODO.

## Acceptance criteria

```bash
# TODO: replace with an executable check (pytest, curl, xcodebuild, …)
pytest -q
```
"""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a new spec from the template.")
    parser.add_argument("kind", choices=sorted(KIND_PREFIX), help="Spec category")
    parser.add_argument("slug", help="Short slug, e.g. voice-barge-in")
    parser.add_argument("title", help="Human-readable spec title")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite if the spec already exists"
    )
    args = parser.parse_args(argv)

    prefix = KIND_PREFIX[args.kind]
    slug = slugify(args.slug)
    if not slug:
        parser.error("slug must contain alphanumeric characters")

    target_dir = SPECS_ROOT / args.kind
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{prefix}-{slug}.md"
    if target.exists() and not args.force:
        print(f"Refusing to overwrite existing spec: {target}", file=sys.stderr)
        return 1

    code = f"{prefix}-{slug.upper().replace('-', '-')}"
    content = TEMPLATE.format(prefix=prefix, slug=slug, title=args.title, code=code)
    target.write_text(content, encoding="utf-8")
    print(f"Created {target.relative_to(SPECS_ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
