---
name: agent-loop
description: Use when running a task through a structured, auditable agent loop — bootstrap_agent -> perceive -> goal_contract -> policy_check -> capability_discovery -> plan -> execute_loop — instead of ad-hoc execution; the engine enforces phase order, gates, and an audit trail. Triggers on "agent loop", "bootstrap_agent", "perceive", "goal_contract", "policy_check", "capability_discovery", "execute_loop", "ลูปเอเจนต์", "วางแผนแบบมีสัญญาเป้าหมาย".
---

# Agent Loop

รันงานผ่าน 7 เฟสตามลำดับ โดย `scripts/run.py` เป็น **state machine ตัวจริง** — บังคับลำดับ, บังคับ gate, และเก็บหลักฐานลง `.agent-loop/<run>.json`
โมเดลทำหน้าที่ตัดสินใจเนื้อหา (task, note, criteria, todos) และตีความผลลัพธ์ — **ไม่ตัดสินลำดับเฟสเอง**

## เฟสและ gate

| # | เฟส | ทำอะไร | gate (ต้องมีก่อนปิดเฟส) |
| - | --- | ------ | ----------------------- |
| 0 | `bootstrap_agent` | สร้าง run + ขอบเขตงาน | `task` (ปิดอัตโนมัติตอน `start`) |
| 1 | `perceive` | รวบรวมบริบท/หลักฐานที่เกี่ยวข้อง | `note` ≥ 10 ตัวอักษร |
| 2 | `goal_contract` | กำหนดเป้าหมาย + acceptance criteria | `criteria` ≥ 1 |
| 3 | `policy_check` | โหลดกฎจาก AGENTS.md (global + ไล่ขึ้นจาก cwd) | engine โหลดเอง ต้องได้ ≥ 1 กฎ |
| 4 | `capability_discovery` | ค้น skills / agents / commands ที่มีอยู่ | engine ค้นเอง ต้องเจอ ≥ 1 สกิล |
| 5 | `plan` | แตกงานเป็น todo | `todos` ≥ 1 |
| 6 | `execute_loop` | ลงมือทำจนครบ DoD + สรุปหลักฐาน | `note` ≥ 10 ตัวอักษร |

## Workflow

```sh
# 0 + 1) bootstrap แล้ว perceive
python scripts/run.py '{"op":"start","task":"<งาน>","criteria":["<เกณฑ์เริ่มต้น>"]}'
python scripts/run.py '{"op":"advance","run":"<id>","note":"บริบทและหลักฐานที่รวบรวมได้"}'

# 2) goal_contract
python scripts/run.py '{"op":"advance","run":"<id>","criteria":["เกณฑ์ 1","เกณฑ์ 2"]}'

# 3) policy_check (engine โหลด AGENTS.md เอง)
python scripts/run.py '{"op":"advance","run":"<id>"}'

# 4) capability_discovery (engine ค้น skills/agents/commands เอง)
python scripts/run.py '{"op":"advance","run":"<id>"}'

# 5) plan
python scripts/run.py '{"op":"advance","run":"<id>","todos":["งานย่อย 1","งานย่อย 2"]}'

# 6) execute_loop — จบแล้ว phase = "done" + summary
python scripts/run.py '{"op":"advance","run":"<id>","note":"สรุปผลที่ทำจริง + หลักฐาน"}'
```

## Ops เสริม

| op | ใช้เมื่อ |
| -- | ------- |
| `{"op":"status","run":"<id>"}` | ดูเฟสปัจจุบัน + gate ถัดไป + history (เว้น `run` = list run ทั้งหมด) |
| `{"op":"policy"}` | ดูกฎที่โหลดได้จาก AGENTS.md โดยไม่ต้องมี run |
| `{"op":"capabilities"}` | ดู skills/agents/commands ที่ discover ได้ |

## กฎ

- gate ไม่ครบ → engine คืน `ok:false` + `missing` (exit 1) → เก็บของให้ครบแล้วเรียกซ้ำ **ห้ามข้ามเฟส**
- `policy_check` / `capability_discovery` เป็นงานของ engine — อย่าไปกรอกข้อมูลเองใน `note`
- ส่ง `dir` เฉพาะเมื่อไม่ได้รันในโฟลเดอร์งาน (ค่า default = cwd); ใช้ path ปกติของ OS
- `.agent-loop/*.json` คือ audit trail — อย่าแก้ด้วยมือ

## Do not

- Do not run `plan` before `goal_contract` — engine จะบล็อก
- Do not invent engine output — always run `scripts/run.py`
- Do not put secrets in `note` / `criteria` / `task` — state file เป็น plaintext ในโปรเจกต์
