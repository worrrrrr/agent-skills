# SPEC — agent-skills

สัญญาเป้าหมายของ repo นี้ ใช้ตัดสินว่า "เสร็จ" หรือยัง โดยไม่ต้องเถียงด้วยความจำ

## 1. เป้าหมาย

ให้ agent รับงาน → เดินจนจบ → คืน **artifact + หลักฐานที่ตรวจซ้ำได้**
ไม่ใช่คำอธิบายว่าเสร็จ และไม่ใช่แค่โค้ดที่ compile ผ่าน

## 2. นิยาม

| คำ | ความหมาย |
| --- | --- |
| skill | โฟลเดอร์ใน `skills/<name>/` ที่มี `SKILL.md` + frontmatter (`name`, `description`) |
| engine | `scripts/run.py` หรือ CLI ที่ skill ประกาศ `smoke:` |
| proof | คำสั่งที่รันจริง + exit code (`by:"engine"`) ไม่ใช่คำประกาศ |
| verified | ทุก todo มี proof จาก engine และ `open=[]` |
| done | สถานะที่ **คำนวณจาก** proof ไม่ใช่ธงที่เขียนไว้ |

## 3. Acceptance criteria

ระบบถือว่าผ่านเมื่อ **ทั้ง 6 ข้อ** เป็นจริง:

1. **Skill contract** — ทุก `skills/*/SKILL.md` มี `name` ตรงโฟลเดอร์, `description` มี "Use when", และ path ที่อ้างมีจริง
2. **README truth** — ตาราง Skills = โฟลเดอร์จริง, คำสั่ง `python skills/<x>/` และลิงก์ relative ชี้ของที่มีอยู่
3. **Engines run** — ทุก skill ที่ประกาศ `smoke:` รันแล้ว exit 0 (หรือ SKIP เพราะ dependency ขาด)
4. **Loop proof** — run ของ agent-loop ถึง `phase=done` ได้เฉพาะเมื่อทุก todo มี engine proof; `status` ต้องได้ `open=[]`, `verified=true`
5. **No raw personal data** — ไฟล์ที่มีวันเกิด/พิกัด/คะแนนดิบ/ข้อมูลสุขภาพ ต้องไม่ถูก track (อยู่ใน `.gitignore`)
6. **Review** — งานที่ไม่จิ๊บจ๊อยผ่านผู้ตรวจ fresh context แล้วไม่มี blocker

## 4. Quality gates (รันก่อนปิดงาน)

```sh
# repo gate
python check.py

# harness (report = verdict) — repo gate + smoke ทุกสกิล
python harness.py --selfcheck

# engine gate (agent-loop, global install)
cd ~/.agents/skills/agent-loop && python -m unittest discover -s tests
```

- gate ใด fail = ยังไม่เสร็จ ห้ามสรุปด้วยคำพูด
- evidence ต้องเป็นคำสั่ง + exit code ไม่ใช่ note

## 5. Non-goals (เฟสนี้)

- **Auto-trigger แบบ hard** (plugin/hook) — รอ API ของ runtime ยืนยัน
- **Semantic proof** — engine พิสูจน์ว่า "คำสั่งรันแล้ว exit 0" ไม่ได้พิสูจน์ว่า "คำสั่งนั้นพิสูจน์งาน"
- **External attestation/signing** — ต้องมี CI/remote trust boundary
- **ติดตั้งข้ามเครื่อง/ข้าม OS** — ยังใช้ junction/copy; ยังไม่มี install test
- **ตีความข้อมูลส่วนบุคคล** — ไม่วินิจฉัย ไม่พยากรณ์บุคคลจริง
- **Hub UI** — `docs/ui-ux-spec.md` เป็นแบบ ไม่ใช่งานที่ต้องส่ง

## 6. Known limits (ยอมรับไว้ ไม่ใช่ซ่อน)

| ข้อจำกัด | ผล |
| --- | --- |
| `op=verify` รัน shell อะไรก็ได้ใน project dir | ต้องมีนโยบาย allowlist ก่อนใช้กับงานเสี่ยง |
| `allow_manual:true` ปิด todo ได้ | run จะติด `verified:false`, `unverified:[...]` |
| proof ยังถูกเลือกโดยโมเดล | คำสั่งผ่านง่าย (เช่น `true`) ยังปิด todo ได้ |
| lock ของ engine ไม่มี heartbeat | งาน > 60 วิอาจถูกแย่ง lock |
| schema 1/2/3 | run เก่าใช้กฎเดิม; ไม่มี migration อัตโนมัติ |
| jobs.py ใช้ `tasklist`/`taskkill` | Windows-first; ยังไม่ทดสอบ Linux |
| การติดตั้งใช้ junction (`install.ps1`) | Windows-first; เครื่องอื่นใช้ copy |

## 7. Change policy

- เปลี่ยนพฤติกรรม engine → ต้องมี test ใหม่ใน `tests/`
- เพิ่ม/ลบ skill → ต้องแก้ README + เพิ่ม `smoke:` ถ้ามี engine
- เปลี่ยน schema → ต้องเขียน migration note ใน `references/notes.md`
- เอกสารใหม่ → ต้องมีลิงก์จาก README หรือไม่ต้องมี
- ข้อมูลส่วนตัว → raw อยู่ local, tracked เฉพาะแบบ neutral/band

## 8. Definition of Done (ต่องาน)

1. artifact มีจริง (ไฟล์/คำสั่ง/ผลลัพธ์)
2. quality gates ผ่าน
3. evidence = คำสั่ง + exit code
4. เอกสารที่เกี่ยวข้อง sync แล้ว
5. งานสำคัญผ่าน fresh review ไม่มี blocker
