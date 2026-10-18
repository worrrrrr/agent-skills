# agent-skills

ชุด Agent Skills ขนาดเล็กสำหรับงานคำนวณ exact/symbolic, โหราศาสตร์, กรอบคิดวิเคราะห์ และวินัยการเขียนโค้ด
ใช้ได้กับ agent ที่รองรับ Agent Skills (OpenCode, Claude Code, Codex, Cursor, ...)
`math`/`w8m` รับ-ส่ง JSON ผ่าน `scripts/run.py`; `astrology` เป็น CLI ที่พิมพ์ข้อความ; `craft` เป็น doctrine ล้วน

## Skills

| Skill | ทำอะไร |
| --- | --- |
| `math` | เครื่องคำนวณ exact — calc, sympy (สมการ/calculus/matrix), z3 (constraint/SAT/prove) ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out + guidance เรียก pyswisseph ตรง ๆ ใน SKILL.md |
| `astrology` | คำนวณดวงเต็มระบบจากวันเกิดเดียว: BaZi (สี่เสา), Western tropical, Vedic sidereal (Lahiri), Human Design + ชั้นอ่านคำทำนายภาษาไทย |
| `w8m` | World 8 Models — เลือกโมเดลคิดที่ตรงโจทย์, แจกชุดคำถาม, ตรวจความครอบคลุมคำตอบ, ประกอบรายงาน ผ่าน `scripts/run.py` |
| `craft` | Doctrine ขั้นต่ำสำหรับเขียน/รีวิวโค้ดและ prompt: minimal diff, พิสูจน์ด้วยคำสั่งจริง, failure path, prompt-as-contract (ไม่มี engine) |

## Docs

- [self-model-template.md](docs/self-model-template.md) — ฟอร์มกลางสำหรับโปรไฟล์/แผน 90 วัน (ไม่มีข้อมูลส่วนตัว)
- [self-model.neutral.md](docs/self-model.neutral.md) — โปรไฟล์แบบ band + กลไก + robustness
- [reading.rules.md](docs/reading.rules.md) — กฎตำรา → ข้อสรุป (BaZi/HD/Western/Vedic/Big Five)
- [habits.neutral.md](docs/habits.neutral.md) — แปลงข้อสรุปเป็นนิสัยที่วัดได้
- [character.example.md](docs/character.example.md) — ตัวอย่างสร้างตัวละครจากกฎ (fiction)

## ติดตั้ง

### ด้วย skills CLI

```sh
npx skills add worrrrrr/agent-skills --list                 # ดูรายชื่อ
npx skills add worrrrrr/agent-skills -a opencode            # ลงเฉพาะโปรเจกต์
npx skills add worrrrrr/agent-skills -g -a opencode -y      # ลง global
```

### ด้วยมือ

| Agent | Global | Project |
| --- | --- | --- |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` |

```sh
mkdir -p ~/.config/opencode/skills
cp -r skills/* ~/.config/opencode/skills/
```

## ตรวจสุขภาพ

```sh
python check.py   # frontmatter, refs, README ↔ skills — exit 1 เมื่อเพี้ยน
```

## Dependency

```sh
pip install sympy z3-solver pyswisseph
```

- `math` ต้องมี `sympy` + `z3-solver`; ส่วน ephemeris ต้องมี `pyswisseph`
- `astrology` ต้องมี `pyswisseph` (แนบ `assets/*.se1` ซึ่งเป็น Swiss Ephemeris data มาให้แล้ว)
- `skills/astrology/scripts/astro.ts` เป็น engine สำรองแบบ zero-dependency (import-only — ใช้ `tsx` รัน driver ที่ import มัน; ความแม่นต่ำกว่า Python)

## ใช้งานเร็ว

```sh
# math
python skills/math/scripts/run.py '{"op":"solve","eq":"x**2 - 5*x + 6 = 0","symbol":"x"}'

# astrology (year month day hour minute lat lon tz)
python skills/astrology/scripts/astrology.py 1992 8 8 16 49 6.53995 101.29 7
python skills/astrology/scripts/reading.py 1992 8 8 16 49 6.53995 101.29 7 m

# w8m — กรอบคิด 8 แบบ: เลือกโมเดลตามโจทย์ / แจกโครง / ตรวจคำตอบ / ประกอบรายงาน
python skills/w8m/scripts/run.py '{"op":"plan","problem":"จะโปรโมตพนักงานดีไหม","k":4}'
python skills/w8m/scripts/run.py '{"op":"analyze","problem":"..."}'
python skills/w8m/scripts/run.py '{"op":"report","problem":"...","answers":{"inversion":"..."}}'
```
