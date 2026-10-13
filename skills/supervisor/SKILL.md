---
name: supervisor
description: ตรวจงานและให้คะแนนแบบหัวหน้างาน — รับชิ้นงานพร้อมเกณฑ์ acceptance แล้ว engine ตรวจความครบถ้วน ให้คะแนน ชี้จุดบกพร่อง และสรุปคำสั่งงานกลับ Triggers on หัวหน้างาน,ตรวจงาน,ให้คะแนน,review work,supervisor,acceptance criteria,เกณฑ์ตรวจงาน.
---

# Supervisor

ตรวจงานและให้คะแนนแบบหัวหน้างาน — รับชิ้นงานพร้อมเกณฑ์ acceptance แล้ว engine ตรวจความครบถ้วน ให้คะแนน ชี้จุดบกพร่อง และสรุปคำสั่งงานกลับ

## Inputs

| Field | Notes |
| ----- | ----- |
| `work` | ข้อความชิ้นงานที่ส่งตรวจ (required, non-empty string) — ถ้าไม่มี ถามผู้ใช้ ห้ามเดา |
| `criteria` | 1..50 เกณฑ์ acceptance (required) — เป็น string หรือ `{"criterion", "must_contain", "must_any"}` |
| `min_score` | เกณฑ์ผ่าน 0..100 (optional, default 60) |

เกณฑ์แบบ string สกัด keyword เอง (ผ่านเมื่อเจอ ≥ 50%); `must_contain` ต้องพบครบทุกตัว; `must_any` พบอย่างน้อย 1 ตัว

## Workflow

1. Validate inputs (fail fast with a clear message).
2. Run the deterministic engine: `python scripts/run.py '<json-input>'`
3. Read `references/notes.md` only if interpretation rules are needed.
4. Translate raw output into plain language (Thai if the user writes Thai).

## Engine

`scripts/run.py` is the source of truth. Never hand-compute its output.

```sh
python scripts/run.py '{"work": "สรุปงาน: มี unit test 42 ตัว ผ่านหมด README อัปเดตแล้ว", "criteria": ["มี unit test ที่ผ่าน", {"criterion": "มี README", "must_contain": ["readme"]}]}'
```

คืน `score` (0..100), `grade` (A-F), `verdict` (`approve`/`revise` เทียบ `min_score`), `gaps`, `next_actions`

## Do not

- Do not invent engine output — always run `scripts/run.py`.
- Do not add dependencies without need.
