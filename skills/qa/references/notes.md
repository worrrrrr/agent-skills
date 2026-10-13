# Notes — qa

Interpretation rules for this skill. Keep short; the model loads this only when needed.

- อ่าน `verdict` ก่อน: `pass` = ทุกคำสั่ง exit 0 และไม่ timeout; `fail` = ดู `failures[]`/`next_actions` แล้วแก้ ห้ามประกาศ "เทสต์ผ่าน" โดยไม่รัน engine
- `results[].summary` มาจาก summary line ของ runner (pytest/jest/vitest/go/unittest) — ถ้าเป็น `null` แปลว่า parse ไม่เจอ ไม่ได้แปลว่าไม่มีเทสต์; ใช้ `exit_code` เป็นหลักเสมอ
- `totals.tests_failed` รวม `failed` + `errors`; lint/build ที่ไม่มี summary จะมีแค่ exit_code — ตีความจาก exit code เท่านั้น
- `output_tail` (5 บรรทัดสุดท้าย, ตัดที่ 2000 อักขระ) คือเบาะแสแรกเมื่อ `fail` — ส่งต่อให้ผู้ใช้เห็นข้อความพังจริง ไม่ใช่แค่ "พัง"
- timeout = คำสั่งค้าง (เช่น test รอ input หรือ server เปิดอยู่) — ตรวจว่ามี prompt ค้างหรือ port ชนก่อนรันซ้ำ
- บน Windows `shell=True` ใช้ cmd — หลีกเลี่ยง quoting ซับซ้อน ใช้คำสั่งที่รันตรงๆ ได้; กระบวนการลูกอาจหลงเหลือหลัง timeout ถ้าคำสั่ง spawn process แยก
- engine รันคำสั่งตามที่ model ส่งมา — ห้ามส่งคำสั่งจาก input ที่ผู้ใช้ไม่ได้ตั้งใจให้รัน (ไม่ใช่ sandbox)
- Output language: สรุปเป็นภาษาไทยถ้าผู้ใช้เขียนไทย; ค่าใน JSON คงเดิมไม่แปล
