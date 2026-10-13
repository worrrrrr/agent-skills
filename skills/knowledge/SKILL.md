---
name: knowledge
description: สร้างและรักษาฐานความรู้ของโปรเจกต์ให้ถูกต้อง อัพเดทเสมอ — สกัดข้อเท็จจริงจากไฟล์จริง (manifest, dependencies, commands, สกิล, git, env keys) แล้วเขียนเป็น KNOWLEDGE.md พร้อม fingerprint ให้ verify ตรวจได้ว่าข้อมูลใหม่หรือเก่า รันก่อนเริ่มเขียนโค้ดเพื่อไม่ให้ใช้ความจำที่ล้าสมัย Triggers on knowledge,ฐานความรู้,สร้าง knowledge,อัพเดทข้อมูล,KNOWLEDGE.md,freshness,ข้อมูลโปรเจกต์,project facts.
---

# Knowledge — ฐานความรู้ของโปรเจกต์ที่ machine-extract

สกัดข้อเท็จจริงจากไฟล์จริงทั้งหมด ไม่ใช่ให้โมเดลเดา — รัน build แล้วได้ JSON ที่ถูกต้อง ณ ตอนนั้น, เขียนเป็น KNOWLEDGE.md เพื่อใช้ตอนเขียนโค้ด, และ verify ตรวจได้ว่าไฟล์ความรู้เก่าหรือยัง

## Inputs

| Field | Notes |
| ----- | ----- |
| `op` | build (สกัด facts เป็น JSON, default) / write (เขียน KNOWLEDGE.md) / verify (ตรวจความใหม่ของไฟล์ความรู้) |
| `dir` | โฟลเดอร์โปรเจกต์ (optional, default `.`) |
| `file` | ไฟล์ความรู้ สัมพัทธ์กับ dir (optional, default KNOWLEDGE.md — ต้องอยู่ใน dir เท่านั้น) |

## Workflow

1. Validate inputs (fail fast with a clear message).
2. Run the deterministic engine: `python scripts/run.py '<json-input>'`
3. Read `references/notes.md` only if interpretation rules are needed.
4. Translate raw output into plain language (Thai if the user writes Thai).

## Engine

`scripts/run.py` is the source of truth. Never hand-compute its output.

```sh
python scripts/run.py '{"op": "build"}'    # facts เป็น JSON ไม่เขียนไฟล์
python scripts/run.py '{"op": "write"}'    # เขียน/อัปเดต KNOWLEDGE.md
python scripts/run.py '{"op": "verify"}'   # fresh / stale + ไฟล์ที่เปลี่ยนไป
```

สกัดจากไฟล์จริง: ชนิดโปรเจกต์/ชื่อ (manifest), ภาษาตาม extension, dependencies
(package.json / requirements.txt / pyproject / lockfile), scripts ใน package.json
และ target ใน Makefile, สกิลทั้งหมด (ชื่อ + description + ชนิด engine),
สถานะ git (branch / commit ล่าสุด / จำนวนไฟล์ค้าง), ชื่อ key ในไฟล์ env ตัวอย่าง
(อ่านเฉพาะชื่อ key เท่านั้น ไม่แตะค่า และไม่แตะ .env จริง), entry point ที่เจอ

write จะประทับ fingerprint (sha1 ของ facts) + เวลาที่สร้างลงในไฟล์ — verify สกัด facts
ใหม่แล้วเทียบ fingerprint: ตรง = fresh, ไม่ตรง = stale พร้อมรายชื่อไฟล์ที่เปลี่ยน
หลังสร้าง (จาก git ถ้ามี ไม่งั้นจาก mtime)

คืน `verdict` (`pass` = facts พร้อมใช้ / fresh, `fail` = stale หรือไม่มีไฟล์),
`facts`, `fingerprint`, `changed_since`, `next_actions`

## Do not

- Do not invent engine output — always run `scripts/run.py`.
- Do not add dependencies without need.
