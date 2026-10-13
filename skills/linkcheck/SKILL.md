---
name: linkcheck
description: ตรวจลิงก์และไฟล์อ้างอิงที่พังในเอกสารแบบรันเองได้ — สแกนไฟล์ Markdown ทั้งหมด (README, docs, SKILL.md) แล้วตรวจ relative link, anchor ในไฟล์ .md ที่อ้างถึง และ path ใน backtick ว่าชี้ถึงไฟล์จริงหรือไม่ พร้อมตัวเลือกเช็ค http link ภายนอก Triggers on linkcheck,ตรวจลิงก์,broken link,ลิงก์พัง,check links,เอกสารพัง,anchor.
---

# Linkcheck — ตรวจลิงก์/ไฟล์อ้างอิงที่พังในเอกสาร

สแกน Markdown ใต้โฟลเดอร์ใดก็ได้แล้วบอกว่าลิงก์ไหนชี้ของจริง ลิงก์ไหนพัง และ backtick path ไหนอ้างไฟล์ที่ไม่มีอยู่ — รันเองได้ ไม่ต้องเตรียม input

## Inputs

| Field | Notes |
| ----- | ----- |
| `dir` | โฟลเดอร์ตั้งต้นของเอกสาร (optional, default `.` = cwd — รันจาก root ของ repo จะตรวจทั้ง repo) |
| `check_http` | ตรวจ http(s) link จริงด้วยหรือไม่ (optional, default false — เปิดเมื่อต้องการยืนยัน link ภายนอกจริง) |
| `timeout` | timeout ต่อ http link วินาที (optional, default 10, max 60) |

## Workflow

1. Validate inputs (fail fast with a clear message).
2. Run the deterministic engine: `python scripts/run.py '<json-input>'`
3. Read `references/notes.md` only if interpretation rules are needed.
4. Translate raw output into plain language (Thai if the user writes Thai).

## Engine

`scripts/run.py` is the source of truth. Never hand-compute its output.

```sh
python scripts/run.py '{}'                      # สแกน cwd ทั้งหมด
python scripts/run.py '{"dir": "docs"}'         # สแกนเฉพาะโฟลเดอร์
python scripts/run.py '{"check_http": true}'    # ตรวจ link ภายนอกด้วย
```

สแกนไฟล์ `.md` ทุกไฟล์ใต้ `dir` (ข้าม `.git`, `node_modules`, โฟลเดอร์ซ่อน) แล้วตรวจ:

1. **markdown link/image** `[text](target)` และ reference definition `[ref]: target`
   - relative target ต้องชี้ถึงไฟล์/โฟลเดอร์จริง (fail ถ้าไม่มี)
   - target เป็น `.md` + `#anchor` → anchor ต้องมีจริงในไฟล์นั้น (GitHub slug ของ heading หรือ `id=`/`name=` ใน HTML)
   - `#anchor` อย่างเดียว = ตรวจในไฟล์เดียวกัน; link `http(s)` = ข้ามเว้นแต่ `check_http: true`
2. **path ใน inline code span** นอก fenced code ที่ลงท้ายด้วย extension ที่รู้จัก (เช่น `scripts/run.py`, `references/notes.md`)
   - resolve จากโฟลเดอร์ไฟล์นั้น → skill root ที่ใกล้ที่สุด (+ `scripts/`) → root → โฟลเดอร์สกิลทุกตัว (+ `scripts/`)
   - ไม่เจอ = **warn** (heuristic — เอกสารมักอ้าง path เป็นแนวคิด เช่น `AGENTS.md` ของโปรเจกต์ผู้ใช้)

คืน `verdict` (`pass`/`fail` จาก link/anchor ที่พัง), `results[]` (ต่อไฟล์ที่มี finding), `totals`, `failures`, `next_actions`

## Do not

- Do not invent engine output — always run `scripts/run.py`.
- Do not add dependencies without need.
