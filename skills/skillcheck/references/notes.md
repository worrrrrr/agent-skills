# Notes — skillcheck

Interpretation rules for this skill. Keep short; the model loads this only when needed.

- อ่าน `verdict` ก่อน: `pass` = ทุกสกิลไม่มี fail finding; `fail` = ดู `failures[]` + `next_actions` แล้วแก้ ห้ามประกาศ "สกิลปกติทุกตัว" โดยไม่รัน engine
- `smoke.status` ตีความ:
  - `accepts` = engine รับ payload ว่าง `{}` ได้ (มักเป็น op แบบ health/echo)
  - `rejects` = engine ปฏิเสธอย่างมีโครงสร้าง (`ok:false` + `error`) — **ปกติ**: แปลว่า import ผ่านและ validation ทำงาน
  - `ok` = custom `smoke:` คำสั่ง exit 0
  - `missing_dependency` = ลง `pip install <pkg>` แล้วรันซ้ำ — เป็นปัญหา **environment ไม่ใช่โค้ด**
  - `invalid_output` = คืน JSON แต่ไม่มี `ok` — ผิด contract ของชุดสกิล
  - `crashed` = ดู `smoke.output_tail` (traceback บรรทัดสุดท้ายคือสาเหตุจริง)
  - `timeout` = engine ค้าง (เช่น รอ input) — ตรวจ prompt ค้างหรือเพิ่ม `smoke:` ที่รันจบได้
  - `skipped` = ไม่มี `scripts/run.py` และไม่ได้ประกาศ `smoke:`; `skipped_self` = skillcheck ข้ามตัวเอง กัน recursion ทั้งคู่ไม่ใช่ failure
- fail vs warn: fail = พังจริง (ไม่มี SKILL.md/scripts, smoke พัง, ไม่ติด README); warn = ควรแก้ (ชื่อไม่ตรงโฟลเดอร์, ไม่มี trigger keywords) — เตือนแต่ไม่ทำให้ `verdict` เป็น fail
- smoke รันด้วย payload `{}` เท่านั้น — engine ที่ต้องการ input จริงควรประกาศ `smoke: <คำสั่งที่รันจบได้>` ใน frontmatter (รันจากโฟลเดอร์สกิล); smoke default ของ JSON engine รันจาก `scripts/`
- README registry check หา `` `<ชื่อสกิล>` `` (มี backtick) ใน `README.md` ข้างโฟลเดอร์ skills — ไม่มี README = ข้ามเงียบๆ ไม่ใช่ fail
- บน Windows คำสั่ง smoke รันผ่าน `shell=True` (cmd) — หลีกเลี่ยง quoting ซับซ้อนใน `smoke:`
- Output language: สรุปเป็นภาษาไทยถ้าผู้ใช้เขียนไทย; ค่าใน JSON คงเดิมไม่แปล
