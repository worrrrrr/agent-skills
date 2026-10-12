---
name: skill-maker
description: Use when creating a new opencode skill as an executable workflow with a deterministic script engine. Triggers on "สร้างสกิล", "new skill", "scaffold skill", "SKILL.md", "workflow skill".
---

# Skill Maker — skill-as-workflow scaffolder

Creates a new skill where deterministic logic lives in `scripts/run.py` and the model only interprets output.

## Workflow

1. Get `name` (kebab-case), one-line `description`, trigger keywords.
2. Run the engine:
```sh
python scripts/scaffold.py <name> --description "..." --triggers "kw1,kw2" --base-dir .opencode/skills
```
3. Implement real logic inside the generated `scripts/run.py` (`run(payload)` function).
4. Put interpretation rules in the generated `references/notes.md`.
5. Restart opencode (config is not hot-reloaded), then test: `python <name>/scripts/run.py '{"input":"example"}'`.

## Do not

- Do not hand-write SKILL.md from scratch — always use `scaffold.py`.
- Do not let the model compute what the script should compute.
