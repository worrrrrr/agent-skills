# Notes — knowledge

Interpretation rules for this skill. Keep short; the model loads this only when needed.

- อ่าน `verdict` ก่อน: `pass` = facts พร้อมใช้ (build/write) หรือไฟล์ความรู้ยังใหม่ (verify); `fail` ใน verify = ข้อมูลเก่าแล้ว — รัน op write แล้วรายงานสิ่งที่เปลี่ยน ห้ามใช้ไฟล์ความรู้เก่าโดยไม่ verify
- `facts` คือความจริง ณ ตอนรัน — ใช้ตอบคำถามเรื่อง commands/dependencies/สกิล/โครงสร้างแทนการเดา หรืออ่านไฟล์มั่ว ๆ เอง
- `fingerprint` (12 ตัวอักษร) = sha1 ของ facts ที่ canonicalize แล้ว — เปลี่ยนเมื่อข้อเท็จจริงเปลี่ยนรวมถึงสถานะ git ด้วย ดังนั้นแก้โค้ดอะไรก็ตาม verify จะเห็น stale ทันที (นี่คือเจตนา: ความรู้ต้องตามสภาพจริง)
- `changed_since` มาจาก git status --porcelain ถ้าอยู่ใน git repo (แม่น) ไม่งั้นจาก mtime (approximate) —  capped ที่ 20 รายการ
- write ปฏิเสธไฟล์ที่มีอยู่แล้วและไม่ได้สร้างโดยสกิลนี้ (ไม่มี fingerprint header) — กันทับไฟล์สำคัญของผู้ใช้; `file` ต้องอยู่ใน `dir` เท่านั้น
- อ่านเฉพาะชื่อ key จากไฟล์ env ตัวอย่าง (.env.example/.env.sample/.env.dist) — ห้ามอ่านค่า และห้ามแตะ .env จริงเด็ดขาด (แม้ว่าจะมีก็ตาม)
- ข้อจำกัด: ไม่ parse lockfile เนื้อหา (นับแค่การมีอยู่), pyproject อ่านด้วย regex ไม่ใช่ TOML parser, Makefile จับ target แบบง่าย — ข้อมูลจริงที่ซับซ้อนให้เปิดไฟล์เอง
- KNOWLEDGE.md ที่ engine เขียนมี fingerprint ใน header — ห้ามแก้ด้วยมือเพราะทำให้ verify อ่านค่าเก่า/ใหม่สับสน; แก้ไขความจริงด้วยการรัน op write ใหม่
- Output language: สรุปเป็นภาษาไทยถ้าผู้ใช้เขียนไทย; ค่าใน JSON คงเดิมไม่แปล
