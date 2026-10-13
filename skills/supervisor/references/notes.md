# Notes — supervisor

Interpretation rules for this skill. Keep short; the model loads this only when needed.

- อ่าน `verdict` ก่อน: `approve` = ผ่านเกณฑ์ (`score >= min_score`), `revise` = ต้องแก้ — `score`/`grade` ใช้สื่อระดับความพร้อม ไม่ใช่เกรดการศึกษา
- `gaps` + `next_actions` คือจุดบกพร่องที่ engine ตรวจจาก keyword จริงใน `work` — เสนอลูกทีมแก้ตามนั้น แล้วรันซ้ำเพื่อยืนยัน ห้ามประกาศผ่านเองโดยไม่รัน engine
- เกณฑ์แบบ string เป็น heuristic (keyword coverage ≥ 50%) — งานที่ใช้คำอื่นแทนที่จะ fail ให้เขียนเกณฑ์ใหม่เป็น object พร้อม `must_contain` ที่ตรงกับคำจริงในชิ้นงาน
- `must_contain` = contract เคร่งครัด ขาดแม้แต่ตัวเดียว = fail; อย่าใส่คำที่ชิ้นงานไม่มีทางเขียนตรงตัว (เช่น คำพ้องความหมาย)
- engine ตรวจข้อความไทย/อังกฤษแบบ case-insensitive และย่อช่องว่าง — แต่ไม่เข้าใจความหมาย ถ้าเกณฑ์ต้องใช้ความเข้าใจบริบท ให้ model ประเมินเองแล้วบันทึกเป็นเกณฑ์ `must_contain` ที่สังเกตได้จากข้อความ
- engine ไม่เข้าใจการปฏิเสธ — "ยังไม่มี test" ยังคง match keyword `test` ถ้าเกณฑ์เป็นเรื่องการมี/ไม่มี ให้ model ตรวจเองแล้วใช้ engine ยืนยันซ้ำด้วยเกณฑ์ที่สังเกตได้
- Output language: สรุปเป็นภาษาไทยถ้าผู้ใช้เขียนไทย; ค่าใน JSON คงเดิมไม่แปล
