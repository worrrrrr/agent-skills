---
name: craft
description: Use when writing, fixing, or reviewing code or production prompts — enforces minimal diff, real verification, failure-path design, and prompt-as-contract. Triggers on "implement", "fix bug", "refactor", "code review", "write a prompt", "system prompt", "แก้โค้ด", "รีวิวโค้ด", "เขียนพรอมป์".
---

# Craft — minimal engineering doctrine

สกัดจากหลักปฏิบัติสาย principal engineer + prompt engineer. เก็บเฉพาะข้อที่เปลี่ยนพฤติกรรมจริง — ตัดข้อที่อ่านแล้วไม่ต้องทำอะไรต่าง.

## ก่อนเขียน

- อ่านไฟล์เป้าหมาย โค้ดข้างเคียง tests และ convention ก่อน — เปลี่ยนให้เข้ากับ idiom ของ repo (ถ้า idiom คือบั๊ก ให้บอกตรง ๆ)
- ถาม why อย่างน้อย 3 ชั้น: อาการ → สาเหตุ → สาเหตุของสาเหตุ ก่อนเลือกวิธีแก้; คำตอบซ้ำ/วกกลับ = ยังไม่ถึงราก
- นิยาม "เสร็จ" เป็นพฤติกรรมที่สังเกตได้; ถ้าโจทย์ไม่ให้มา ให้ตั้งเองแล้วกำกับ
- วางแผนประโยคเดียว: ไฟล์ที่จะแตะ, edge cases, คำสั่งพิสูจน์

## โค้ด

- Minimal diff — ไม่มี refactor/จัดฟอร์แมต/ของแถมที่ไม่มีใครขอ
- ออกแบบเล็กสุดที่ผ่าน requirement; dependency ใหม่ต้องจ่ายค่าตัวเองได้
- Validate ที่ขอบระบบ, trust type/invariant ข้างใน; ห้ามกลืน error
- ทุก I/O มี timeout + failure mode; auth fail closed; secret ห้ามอยู่ในโค้ด/log
- งานที่ย้อนกลับยาก/แตะข้อมูล ต้องมี rollback path และระบุ data-loss surface
- เทสต์ที่คุ้มเขียน: ยืนยัน behavior + ขอบ (ว่าง/null/มาก/ซ้ำ/concurrent/partial) ตามขนาดและความเสี่ยงของงาน; ห้ามแก้เทสต์ให้ผ่าน
- ชื่อคือ API; comment อธิบาย why ไม่ใช่ what

## Prompt

- Prompt คือสัญญา: input shape, output shape, invariant, พฤติกรรมเมื่อล้มเหลว
- ทุกบรรทัดต้องเปลี่ยนพฤติกรรม model — ถ้าไม่ ตัดทิ้ง
- ระบุ format ให้ชัด + fallback เมื่อ input ไม่ครบ; ความกำกวมคือบั๊ก
- ห้ามบอกว่า "ใช้ได้" ถ้าไม่มี test set + metric + ผลก่อน/หลัง

## ตรวจ

รันคำสั่งตรวจที่มีอยู่และเหมาะกับขนาดงาน (test/typecheck/lint) แล้วรายงานคำสั่งนั้นกับสิ่งที่ยังไม่ได้รัน. อ่าน diff แบบ reviewer ที่เป็นศัตรู: coupling ซ่อน, พฤติกรรมเปลี่ยนเงียบ ๆ, path ที่ไม่ handle, ชื่อหลอก, ข้อเท็จจริงที่กุขึ้น.

## รายงาน

change → why (บรรทัดเดียว) → คำสั่งพิสูจน์ → edge ที่จัดการ/ไม่จัดการ → rollback + สมมติฐาน. ข้อความที่ยังไม่ยืนยันให้ติดป้าย `unverified`; ตัวเลขที่กะเอาให้ติด `[ESTIMATE]`.
