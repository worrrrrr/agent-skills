#!/usr/bin/env python3
"""Scaffold a new opencode skill as an executable workflow.
Usage:
  python scaffold.py <skill-name> --description "..." --triggers "kw1,kw2" [--base-dir .opencode/skills]
Creates: <base>/<name>/SKILL.md + scripts/run.py + references/notes.md
"""
import argparse
import re
import sys
from pathlib import Path


def slug(s: str) -> str:
    s = s.strip().lower().replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s or len(s) > 64:
        raise ValueError("name must be 1-64 chars, lowercase hyphen-separated")
    return s


SKILL_TMPL = """---
name: {name}
description: {description} Triggers on {triggers}.
---

# {title}

{description}

## Inputs

| Field | Notes |
| ----- | ----- |
| `input` | Describe required input; if missing, ask the user — do not guess |

## Workflow

1. Validate inputs (fail fast with a clear message).
2. Run the deterministic engine: `python scripts/run.py '<json-input>'`
3. Read `references/notes.md` only if interpretation rules are needed.
4. Translate raw output into plain language (Thai if the user writes Thai).

## Engine

`scripts/run.py` is the source of truth. Never hand-compute its output.

```sh
python scripts/run.py '{{"input": "example"}}'
```

## Do not

- Do not invent engine output — always run `scripts/run.py`.
- Do not add dependencies without need.
"""

RUN_TMPL = '''#!/usr/bin/env python3
"""Deterministic engine for skill: {name}. Replace TODO with real logic."""
import json
import sys


def run(payload: dict) -> dict:
    # TODO: implement real computation here
    return {{"ok": True, "skill": "{name}", "echo": payload}}


def main() -> None:
    raw = sys.argv[1] if len(sys.argv) > 1 else '{{}}'
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"invalid JSON input: {{e}}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(run(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
'''

REF_TMPL = """# Notes — {name}

Interpretation rules for this skill. Keep short; the model loads this only when needed.

- Rule 1: describe how to read engine output.
- Rule 2: edge cases and boundaries.
- Rule 3: output language and format.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--description", required=True)
    ap.add_argument("--triggers", default="")
    ap.add_argument("--base-dir", default=".opencode/skills")
    a = ap.parse_args()

    name = slug(a.name)
    base = Path(a.base_dir) / name
    if base.exists():
        print(f"exists: {base}", file=sys.stderr)
        sys.exit(1)

    (base / "scripts").mkdir(parents=True)
    (base / "references").mkdir(parents=True)
    title = name.replace("-", " ").title()
    (base / "SKILL.md").write_text(
        SKILL_TMPL.format(
            name=name, title=title,
            description=a.description.strip(),
            triggers=a.triggers.strip() or "keywords for this skill",
        ),
        encoding="utf-8",
    )
    (base / "scripts" / "run.py").write_text(
        RUN_TMPL.format(name=name), encoding="utf-8"
    )
    (base / "references" / "notes.md").write_text(
        REF_TMPL.format(name=name), encoding="utf-8"
    )
    print(str(base / "SKILL.md"))
    print(str(base / "scripts" / "run.py"))
    print(str(base / "references" / "notes.md"))


if __name__ == "__main__":
    main()
