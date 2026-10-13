# Notes — linkcheck

Interpretation rules for this skill. Keep short; the model loads this only when needed.

- อ่าน `verdict` ก่อน: `pass` = ลิงก์/anchor ไม่มีตัวไหนพัง; `fail` = ดู `failures[]` + `next_actions` แล้วแก้ ห้ามประกาศ "เอกสารไม่มีลิงก์พัง" โดยไม่รัน engine
- severity: **fail** = md link target ไม่มีจริง / anchor ไม่มีในไฟล์ที่อ้าง (สัญญาณชัดเจน ผู้เขียนตั้งใจลิงก์); **warn** = code-span path ไม่ resolve (heuristic — มักเป็นการอ้างแบบแนวคิด เช่น `AGENTS.md` ของโปรเจกต์ผู้ใช้ หรือ `globals.css` ในสเปก — เตือนไม่ทำให้ verdict เป็น fail)
- ตรวจเฉพาะ inline code span **นอก** fenced code block (```) — ตัวอย่างใน fence เป็นค่าสมมติ (เช่น `problems43.txt`) ไม่ใช่ไฟล์จริง ห้ามนับเป็น finding
- anchor ตรวจแบบ GitHub slug: lowercase, ตัดอักขระวรรคตอน, ช่องว่าง → `-`, คงอักษรไทย/`-`/`_`; duplicate heading ได้ suffix `-1`, `-2` (engine ไม่รองรับ suffix นี้ — ถ้า anchor ที่หายเป็น duplicate ให้แก้เป็น link เต็มทาง)
- `#L10` / `#L10-L20` (line anchor) และ anchor ในไฟล์ non-.md ถูกข้าม — ตรวจ content ไม่ได้ ไม่ใช่ลิงก์พัง
- `results[]` มีเฉพาะไฟล์ที่มี finding; ไฟล์สะอาดถูกนับใน `totals` เฉยๆ; finding ซ้ำในไฟล์เดียวกันถูกรวมเป็นบรรทัดเดียวพร้อม `count`
- `check_http: true` ใช้ network — ผล `external_broken` (status code) / `external_error` (network) แยกกัน; ช้าหรือ fail ได้ตามสภาพเน็ต ถ้าไม่สำคัญอย่าเปิด
- บน Windows engine รันด้วย Python มาตรฐานล้วน (ไม่มี subprocess) — เสถียรกว่า skillcheck ที่ smoke-run engine จริง
- Output language: สรุปเป็นภาษาไทยถ้าผู้ใช้เขียนไทย; ค่าใน JSON คงเดิมไม่แปล
