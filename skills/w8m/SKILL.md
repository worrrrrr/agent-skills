---
name: w8m
description: Use when analyzing a problem, decision, plan, or trade-off with structured thinking models. Covers first principles, inversion, second-order thinking, expected value, base rate, Occam, feedback loops, and margin of safety. Triggers on "วิเคราะห์", "ตัดสินใจ", "ควรไหม", "คุ้มไหม", "trade-off", "pre-mortem", "first principles", "inversion", "second-order", "expected value", "base rate", "occam", "feedback loop", "margin of safety", "โครงคำถาม".
smoke: python scripts/run.py '{"op":"list"}'
---

# w8m — World 8 Models

กรอบคิด 8 แบบสำหรับวิเคราะห์ปัญหา/การตัดสินใจ. Engine **ไม่ได้คิดเอง** — มันเลือกโมเดลที่ตรงโจทย์, แจกชุดคำถาม, ตรวจว่าคำตอบครบหรือยัง, และประกอบ markdown จากคำตอบที่ agent เขียน. ตัววิเคราะห์คือคุณ.

| id | ใช้เมื่อ |
| --- | --- |
| `first-principles` | โจทย์เต็มไปด้วยศัพท์วงใน/สมมติฐานที่ไม่ได้ตรวจ |
| `inversion` | อยากกันความล้มเหลว, pre-mortem, หาทางสำเร็จไม่เจอ |
| `second-order` | ผลลัพธ์จะไปกระทบอะไรต่อ (และแล้วไง) |
| `expected-value` | ตัดสินภายใต้ความน่าจะเป็น/กำไรขาดทุน |
| `base-rate` | มีเรื่องเล่ากรณีเดียว แต่ยังไม่ดูสถิติของกลุ่ม |
| `occam` | มีหลายคำอธิบาย/หลายทางเลือกที่ดูพอ ๆ กัน |
| `feedback-loop` | ระบบมีวงจรเร่ง/ถอย หรือมีความหน่วง |
| `margin-of-safety` | ออกแบบใกล้ขีดจำกัด ต้องเผื่อค่าที่ประมาณผิด |

## Engine

`scripts/run.py` — JSON เข้า/ออก, op: `list | show | plan | analyze | report`

```sh
python scripts/run.py '{"op":"list"}'
python scripts/run.py '{"op":"show","id":"inversion"}'
python scripts/run.py '{"op":"plan","problem":"จะโปรโมตพนักงานดีไหม","k":4}'
python scripts/run.py '{"op":"analyze","problem":"...","answers":{"inversion":"..."}}'
python scripts/run.py '{"op":"report","problem":"...","answers":{"inversion":{"วิธีทำให้พัง":"..."}}}'
```

- `plan` จับ tag ในโจทย์แล้วเลือก `k` โมเดล (clamp 2–8); ไม่พบ tag → ชุดเริ่มต้น first-principles + inversion + second-order + occam แล้วตัด/เติมให้ครบ `k` (`matched_by_tags:false`)
- `analyze` คืน scaffold (questions/steps/deliverable/red_flags) และถ้าส่ง `answers` มาจะได้ `coverage` (missing/empty_fields/ignored/progress)
- `report` คืน `{markdown, coverage, gaps}` — ห้ามแต่งคำตอบแทน ให้ส่งเฉพาะ answers ที่มีจริง
- `plan`/`analyze`/`report` รับ `{"models":["inversion","base-rate"]}` เพื่อบังคับชุดโมเดล; id ที่ไม่รู้จัก → error

## Workflow

1. `plan` (หรือ `analyze`) เพื่อเลือกโมเดลและได้คำถาม
2. ตอบ `questions` ของแต่ละโมเดลด้วยข้อเท็จจริงของโจทย์ — ใส่ `deliverable` ให้ครบ
3. ยิง `analyze` พร้อม `answers` เพื่อเช็ค `coverage`; เติมช่องที่ `missing`/`empty_fields`
4. `report` เอา markdown ไปใช้; ถ้า `coverage.complete:false` ให้บอกผู้ใช้ตรง ๆ ว่ายังขาดอะไร

## กฎ

- Engine เป็น heuristic ไม่ใช่ LLM — อย่าให้มันสรุปแทน และอย่าถือ `matched_by_tags` เป็นคำตัดสิน
- ถ้าโมเดลที่เลือกไม่ตรงโจทย์ ให้ส่ง `models` เอง ดีกว่าเชื่อ tag
- คำตอบต้องอ้างข้อเท็จจริง/ตัวเลขจากโจทย์ ไม่ใช่คำคม
