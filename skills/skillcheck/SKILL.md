---
name: skillcheck
description: ตรวจสุขภาพชุดสกิลแบบรันเองได้ด้วยคำสั่งเดียว ไม่ต้องเตรียม input — ค้น skill ทุกตัวในโฟลเดอร์ ตรวจโครงสร้าง SKILL.md + registry แล้ว smoke-run engine แต่ละตัวด้วย payload ว่าง เพื่อบอกว่าตัวไหนใช้ได้จริงในสภาพแวดล้อมนี้ และ dependency ตัวไหนขาด Triggers on skillcheck,ตรวจสกิล,check skills,smoke test,สกิลพัง,skill health,เช็คสกิล.
---

# Skillcheck — ตรวจสุขภาพชุดสกิลแบบรันเองได้

รันคำสั่งเดียวโดยไม่ต้องเตรียมอะไร — engine ค้น skill เอง ตรวจโครงสร้างเอง smoke-run เอง แล้วบอกว่าสกิลไหนใช้ได้จริงในสภาพแวดล้อมนี้ (และขาด dependency อะไร)

## Inputs

| Field | Notes |
| ----- | ----- |
| `dir` | โฟลเดอร์ที่เก็บ skill (optional — default: `./skills` ถ้ามี, ไม่งั้นใช้โฟลเดอร์ skills ที่สกิลนี้ติดตั้งอยู่ รันจากที่ไหนก็ได้) |
| `timeout` | timeout ต่อ engine วินาที (optional, default 20, max 120) |
| `only` | list ของชื่อสกิล (ชื่อโฟลเดอร์) ที่จะเช็คเฉพาะตัว (optional — default ทั้งหมด) |

## Workflow

1. Validate inputs (fail fast with a clear message).
2. Run the deterministic engine: `python scripts/run.py '<json-input>'`
3. Read `references/notes.md` only if interpretation rules are needed.
4. Translate raw output into plain language (Thai if the user writes Thai).

## Engine

`scripts/run.py` is the source of truth. Never hand-compute its output.

```sh
python scripts/run.py '{}'                        # เช็คทั้งโฟลเดอร์ skills
python scripts/run.py '{"only": ["math"]}'        # เช็คเฉพาะสกิลที่ระบุ
python scripts/run.py '{"timeout": 60}'           # ขยาย timeout ต่อ engine
```

engine ทำเองทั้งหมดโดยไม่ต้อง input:

1. **ค้น** skill ทุกโฟลเดอร์ใน `dir` (โฟลเดอร์ที่ขึ้นต้นด้วย `.`/`_` ถูกข้าม)
2. **ตรวจโครงสร้าง**: มี `SKILL.md` + frontmatter (`name`, `description` พร้อม trigger) + `scripts/`; ชื่อ `name` ตรงกับชื่อโฟลเดอร์; มีบรรทัด `` `name` `` ใน README registry (ข้ามถ้าไม่มี README)
3. **smoke-run engine**: รัน `python scripts/run.py '{}'` (หรือคำสั่ง `smoke:` ใน frontmatter ถ้าสกิลนั้นประกาศไว้) แล้วจำแนกสถานะ:
   - `accepts` / `rejects` / `ok` = **แข็งแรง** — engine รันจบและคืน JSON ตาม contract (`rejects` ปกติ: แปลว่า import ผ่านและ validate ทำงาน)
   - `missing_dependency` = ขาด pip package (จับจาก `ModuleNotFoundError`, พร้อมชื่อ package ใน `next_actions`)
   - `invalid_output` = คืน JSON แต่ไม่มี field `ok`
   - `crashed` = ไม่คืน JSON (traceback) / custom smoke ออก nonzero
   - `timeout` = ค้างเกิน timeout
   - `skipped` / `skipped_self` = ไม่มี engine ให้ตรวจ / skillcheck ข้ามตัวเองกัน recursion

คืน `verdict` (`pass`/`fail` จาก fail findings ทุกตัว), `results[]` (engine, smoke, findings), `totals`, `failures`, `next_actions`

## Do not

- Do not invent engine output — always run `scripts/run.py`.
- Do not add dependencies without need.
