---
name: qa
description: รัน test/lint/build จริงแล้วสรุปผลเป็น JSON แบบ deterministic — เก็บ exit code, จำนวนเทสต์ที่ผ่าน/พัง, เวลา และความล้มเหลว ให้ supervisor ใช้เป็นหลักฐานตรวจงาน Triggers on qa,รันเทสต์,run tests,test,lint,build,ตรวจสอบ build,CI,เทสต์ผ่าน.
---

# Qa

รัน test/lint/build จริงแล้วสรุปผลเป็น JSON แบบ deterministic — เก็บ exit code, จำนวนเทสต์ที่ผ่าน/พัง, เวลา และความล้มเหลว ให้ supervisor ใช้เป็นหลักฐานตรวจงาน

## Inputs

| Field | Notes |
| ----- | ----- |
| `commands` | 1..20 คำสั่ง test/lint/build (required) — string หรือ `{"cmd", "name", "timeout"}` — ถ้าไม่รู้ว่า repo ใช้คำสั่งไหน ดูจาก package.json / Makefile / pytest config แล้วถามผู้ใช้ถ้าไม่แน่ใจ |
| `dir` | working directory (optional, default cwd) — ต้องมีอยู่จริง |
| `timeout` | timeout ต่อคำสั่ง วินาที (optional, default 120, max 600) |

## Workflow

1. Validate inputs (fail fast with a clear message).
2. Run the deterministic engine: `python scripts/run.py '<json-input>'`
3. Read `references/notes.md` only if interpretation rules are needed.
4. Translate raw output into plain language (Thai if the user writes Thai).

## Engine

`scripts/run.py` is the source of truth. Never hand-compute its output.

```sh
python scripts/run.py '{"commands": ["python -m pytest -q", {"cmd": "npm run lint", "name": "lint"}]}'
```

คืน `verdict` (`pass`/`fail` จาก exit code ทุกคำสั่ง), `results[]` (exit_code, duration_ms, summary จำนวนเทสต์, output_tail), `totals`, `failures`, `next_actions`

## Do not

- Do not invent engine output — always run `scripts/run.py`.
- Do not add dependencies without need.
