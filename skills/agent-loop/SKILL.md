---
name: agent-loop
description: Use when running a task through a structured, auditable agent loop — bootstrap_agent -> perceive -> goal_contract -> policy_check -> capability_discovery -> plan -> execute_loop — instead of ad-hoc execution; the engine enforces phase order, gates, and an audit trail. Triggers on "agent loop", "bootstrap_agent", "perceive", "goal_contract", "policy_check", "capability_discovery", "execute_loop", "ลูปเอเจนต์", "วางแผนแบบมีสัญญาเป้าหมาย".
---

# Agent Loop

รันงานผ่าน 7 เฟสตามลำดับ โดย `scripts/run.py` เป็น **state machine ตัวจริง** — บังคับลำดับ, บังคับ gate, และเก็บหลักฐานลง `.agent-loop/<run>.json`
โมเดลทำหน้าที่ตัดสินใจเนื้อหา (task, note, criteria, todos) และตีความผลลัพธ์ — **ไม่ตัดสินลำดับเฟสเอง**

## เฟสและ gate

| # | เฟส | ทำอะไร | gate (ต้องมีก่อนปิดเฟส) | ใครให้ |
| - | --- | ------ | ----------------------- | ------ |
| 0 | `bootstrap_agent` | สร้าง run + ขอบเขตงาน | `task` | โมเดล (ปิดอัตโนมัติตอน `start`) |
| 1 | `perceive` | รวบรวมบริบท/หลักฐานที่เกี่ยวข้อง | `note` ≥ 10 ตัวอักษร | โมเดล |
| 2 | `goal_contract` | กำหนดเป้าหมาย + acceptance criteria | `criteria` ≥ 1 | โมเดล |
| 3 | `policy_check` | โหลดกฎจาก AGENTS.md | ได้ ≥ 1 กฎ | engine |
| 4 | `capability_discovery` | ค้น skills/agents/commands ที่ใช้ได้ | เจอ ≥ 1 และ `note` ต้อง**ระบุชื่อ** capability อย่างน้อย 1 ตัว | engine + โมเดล |
| 5 | `plan` | แตกงานเป็น todo | `todos` ≥ 1 | โมเดล |
| 6 | `execute_loop` | ลงมือทำจนครบ DoD + สรุปหลักฐาน | `note` ≥ 10 ตัวอักษร | โมเดล |

## Workflow

```sh
# 0+1) bootstrap แล้ว perceive
python scripts/run.py '{"op":"start","task":"<งาน>"}'
python scripts/run.py '{"op":"advance","run":"<id>","note":"บริบทและหลักฐานที่รวบรวมได้"}'

# 2) goal_contract — criteria รับเฉพาะเฟสนี้
python scripts/run.py '{"op":"advance","run":"<id>","criteria":["เกณฑ์ 1","เกณฑ์ 2"]}'

# 3) policy_check — engine โหลด AGENTS.md เอง
python scripts/run.py '{"op":"advance","run":"<id>"}'

# 4) capability_discovery — engine ค้นเอง แต่ note ต้องระบุชื่อที่เจอ
python scripts/run.py '{"op":"advance","run":"<id>","note":"จะใช้ skill math + agent ผู้รีวิว"}'

# 5) plan — todos รับเฉพาะเฟสนี้
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

- gate ไม่ครบ → คืน `ok:false` + `missing` (exit 1) **ความพยายามที่ถูกบล็อกจะถูกบันทึกใน `history` พร้อมนับใน `blocked_attempts`** — เติมของให้ครบแล้วเรียกซ้ำ ไม่ใช่ข้าม
- `criteria` รับเฉพาะตอนปิด `goal_contract`; `todos` รับเฉพาะตอนปิด `plan` — เฟสอื่นส่งมาแล้วจะถูกปฏิเสธ (กันการ pre-fill ให้ gate กลายเป็นพิธี)
- `policy_check` / `capability_discovery` เป็นงานของ engine: ข้อมูลที่บันทึกเป็นของ engine เอง (`note` ที่ส่งไปจะถูกใช้แค่เฟส 4 เพื่อยืนยันว่าเลือก capability จริง)
- exit code: `0` สำเร็จ / `1` gate ไม่ผ่าน หรือ engine error / `2` input ผิดรูปแบบ — ทุกกรณีคืน JSON บน stdout เสมอ
- ส่ง `dir` เฉพาะเมื่อไม่ได้รันในโฟลเดอร์งาน (ค่า default = cwd) และโฟลเดอร์นั้นต้องมีอยู่จริง
- `.agent-loop/*.json` คือ audit trail — อย่าแก้ด้วยมือ

## Do not

- Do not run `plan` before `goal_contract` — engine จะบล็อก
- Do not invent engine output — always run `scripts/run.py`
- Do not put secrets in `note` / `criteria` / `task` — state file เป็น plaintext ในโปรเจกต์
