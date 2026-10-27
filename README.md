# agent-skills

ชุดเครื่องมือขนาดเล็กสำหรับ agent: **prompt เดียวที่บอกวิธีคิด/วิธีทำงานของเจ้าของ** + **5 skills ที่คำนวณได้จริง**
ทุกอย่างรันด้วย Python, ไม่มี network, และมีตัวตรวจที่รันซ้ำได้ในเครื่องเดียว

- ตัวหลัก: [`owner.prompt.md`](owner.prompt.md) — copy ไฟล์เดียวเข้า agent ตัวไหนก็ได้
- ตัวคำนวณ: `skills/{math, astrology, w8m, spec-guard}` (JSON-in/JSON-out) + `craft` (doctrine)
- ตัวติดตั้ง: [`install.ps1`](install.ps1) — ใช้ได้ทั้งจาก repo และจาก zip ที่ดาวน์โหลดมา

## เริ่มเร็ว 3 ขั้น

```powershell
# 1) ติดตั้ง (จาก zip ที่ดาวน์โหลด หรือจาก repo)
powershell -ExecutionPolicy Bypass -File install.ps1 -FromZip .\dist\agent-skills-0.3.1.zip -Copy

# 2) ตรวจว่าติดตั้งครบ
python check.py

# 3) ตรวจว่าทุก skill ทำงานได้ (รัน smoke จากสำเนา รวมถึง zip)
python -m unittest discover -s tests
```

ผลที่ได้: `~/.agents/owner.prompt.md` และ `~/.agents/skills/{astrology,craft,math,spec-guard,w8m}`

## owner.prompt.md — ตัวหลัก

prompt เดียว (134 บรรทัด, ~12 KB) ที่สรุปวิธีทำงานของเจ้าของ ใช้ได้กับ agent ทุกตัวที่รับ system prompt
(OpenCode / Claude Code / Codex / Cursor / agent ที่อ่าน AGENTS.md)

มีอะไรข้างใน:

| ส่วน | บังคับอะไร |
| --- | --- |
| 3 ด่านก่อนตอบ | slot ที่โจทย์ไม่ได้ให้ · scope/base-rate/แหล่งข้อมูล · ชั้นหลักฐาน E1-E5 |
| กฎการทำงาน 8 ข้อ | พิสูจน์ด้วยการรัน · minimal diff · failure path · learn ไม่ใช่ loop · timebox · ห้ามให้ผู้ใช้เป็น log · ไม่เขียนทับของคนอื่น · ปิดวงจรด้วยสมมติฐานที่ตรวจได้ |
| สิ่งที่ห้ามทำ | กุตัวเลข/แหล่งอ้าง · เติมคำที่โจทย์ไม่ได้เขียน · ประกาศเสร็จโดยไม่ตรวจ |
| รูปแบบผลลัพธ์ 3 แบบ | คำตอบทั่วไป · รายงานงานที่ทำ · รายงานเมื่อเจอปัญหา |
| self-check 5 ข้อ | ถามก่อนส่งทุกครั้ง (ช่องที่เติมเอง / E4 ที่อ้างเป็นข้อเท็จจริง / คำว่า "เสร็จ" / determinism / ประโยชน์ต่อการตัดสินใจ) |
| H17 | ขยายแล้วต้องยุบ: ประกาศ "ชิ้นเดียวที่พกได้" + รายงาน `peak → current` |
| ภาคผนวก | หลักการ 12 ข้อ + เกณฑ์ว่า "เสร็จ" |

`tests/test_owner_prompt.py` ตรวจว่า prompt ยังมีกฎครบ (13 คำสำคัญ), ไม่มีอีโมจิ, ไม่มีอักษรต่างภาษา

## Skills

| Skill | ทำอะไร |
| --- | --- |
| `math` | เครื่องคำนวณ exact — calc, sympy (สมการ/calculus/matrix), z3 (constraint/SAT/prove) ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out + guidance เรียก pyswisseph ตรง ๆ ใน SKILL.md |
| `astrology` | คำนวณดวงเต็มระบบจากวันเกิดเดียว: BaZi (สี่เสา), Western tropical, Vedic sidereal (Lahiri), Human Design + ชั้นอ่านคำทำนายภาษาไทย |
| `w8m` | World 8 Models — เลือกโมเดลคิดที่ตรงโจทย์, แจกชุดคำถาม, ตรวจความครอบคลุมคำตอบ, ประกอบรายงาน ผ่าน `scripts/run.py` |
| `spec-guard` | ตรวจ SPEC-POS-001: layout backend/frontend + 4 แกน, scope boom (authored vs generated), abandonment risk — ใช้ก่อนเปิดโปรเจกต์ใหม่ |
| `craft` | Doctrine ขั้นต่ำสำหรับเขียน/รีวิวโค้ดและ prompt: minimal diff, พิสูจน์ด้วยคำสั่งจริง, failure path, prompt-as-contract (ไม่มี engine) |

## ติดตั้ง

| วิธี | คำสั่ง | ผล |
| --- | --- | --- |
| จาก zip (แนะนำ — พกพาได้) | `install.ps1 -FromZip .\dist\agent-skills-<version>.zip -Copy` | สำเนาลง `~/.agents/` |
| จาก repo (single source) | `install.ps1` | junction ลง `~/.agents/skills/` |
| ด้วยมือ (Linux/macOS) | `cp -r skills/* ~/.agents/skills/` | สำเนา |

ปลายทางที่ agent ต่าง ๆ อ่าน:

| Runtime | Global |
| --- | --- |
| generic (ที่ `install.ps1` ใช้) | `~/.agents/skills/` + `~/.agents/owner.prompt.md` |
| OpenCode | `~/.config/opencode/skills/` (คัดลอกเองหรือ symlink) |

`install.ps1` ไม่ทับโฟลเดอร์ที่มีอยู่แล้วและไม่ใช่ junction (จะข้ามและบอก) — ปลอดภัยเมื่อรันซ้ำ

## แพ็กเกจแจกจ่าย (dist)

```sh
python scripts/build_dist.py --version 0.3.1
```

ได้ `dist/agent-skills-<version>.zip` + `dist/MANIFEST.json` (sha256 ของทุกไฟล์)
zip **ไม่รวม** ephemeris `.se1` ของ astrology (3.5 MB) เพื่อให้ไฟล์เล็ก — ถ้าต้องการ offline เต็มให้คัดลอกจาก repo เอง

`tests/test_dist.py` ตรวจว่าแตก zip แล้ว: manifest ตรงกับไฟล์ใน archive และ smoke ของทุก skill ยังผ่าน

## ตรวจสุขภาพ

```sh
python check.py                              # frontmatter, refs, README ↔ skills (PASS 5 skills)
python -m unittest discover -s tests         # 21 tests
python harness.py --selfcheck                # repo gate + smoke ทุกสกิลในคำสั่งเดียว
```

## Harness

รันงานเป็นชุด check แล้วให้ **report เป็นตัวบอกผล** (verdict มาจาก exit code ไม่ใช่คำอธิบาย)

```sh
python harness.py '{"op":"run","task":"ปิดรอบ repo","checks":[
  {"id":"repo","cmd":"python check.py"},
  {"id":"math","skill":"math"}]}'
python harness.py '{"op":"list"}'
python harness.py '{"op":"status","run":"<id>"}'
```

- check แบบ `skill` อ่าน `smoke:` จาก `SKILL.md` ของสกิลนั้น (ไม่ hardcode)
- check แบบ `agent_loop_run` ผ่านเฉพาะเมื่อ run นั้น `phase=done`, `open=[]`, `verified=true`

## Docs

- [SPEC.md](SPEC.md) — สัญญาเป้าหมาย + acceptance criteria + known limits
- [self-model-template.md](docs/self-model-template.md) — ฟอร์มกลางสำหรับโปรไฟล์/แผน 90 วัน
- [self-model.neutral.md](docs/self-model.neutral.md) — โปรไฟล์แบบ band + กลไก + robustness
- [reading.rules.md](docs/reading.rules.md) — กฎตำรา → ข้อสรุป (BaZi/HD/Western/Vedic/Big Five)
- [habits.neutral.md](docs/habits.neutral.md) — แปลงข้อสรุปเป็นนิสัยที่วัดได้
- [character.example.md](docs/character.example.md) — ตัวอย่างสร้างตัวละครจากกฎ (fiction)
- [ui-ux-spec.md](docs/ui-ux-spec.md) — สเปก UI/UX ที่ใช้อ้างอิง

## Dependency

```sh
pip install sympy z3-solver pyswisseph
```

- `math` ต้องมี `sympy` + `z3-solver`
- `astrology` ต้องมี `pyswisseph` (แนบ `assets/*.se1` มาให้แล้ว)
- `skills/astrology/scripts/astro.ts` เป็น engine สำรอง zero-dependency (import-only, ความแม่นต่ำกว่า Python)

## ตัวอย่าง

```sh
# math
python skills/math/scripts/run.py '{"op":"solve","eq":"x**2 - 5*x + 6 = 0","symbol":"x"}'

# spec-guard (ตรวจโปรเจกต์)
python skills/spec-guard/scripts/run.py '{"op":"check","target":"C:/path/to/project"}'

# w8m
python skills/w8m/scripts/run.py '{"op":"plan","problem":"จะโปรโมตพนักงานดีไหม","k":4}'

# astrology (year month day hour minute lat lon tz)
python skills/astrology/scripts/astrology.py 1992 8 8 16 49 6.53995 101.29 7
```

## สถานะและข้อจำกัด

| ของ | สถานะ |
| --- | --- |
| `check.py` + 21 tests | ผ่านในเครื่องนี้ |
| portability (copy skill ออกนอก repo แล้ว smoke) | ผ่าน 4 skills ที่มี engine |
| `install.ps1 -FromZip` | ผ่าน (แตก zip แล้ว smoke จากสำเนา) |
| Windows junction | ต้องรันเองบนเครื่องปลายทาง |
| `npx skills add <owner>/<repo>` | **ยังไม่ยืนยัน** — CLI ภายนอก ต้องมี network และตัว CLI |
| ephemeris `.se1` | ไม่อยู่ใน zip (คัดลอกจาก repo) |
