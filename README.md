# agent-skills

ชุด Agent Skills สำหรับงานคำนวณแบบ exact/symbolic และโหราศาสตร์เต็มระบบ
ใช้ได้กับ agent ที่รองรับ Agent Skills (OpenCode, Claude Code, Codex, Cursor, ...)

## Skills

| Skill | ทำอะไร |
| --- | --- |
| `math` | เครื่องคำนวณ exact — calc, sympy (สมการ/calculus/matrix), z3 (constraint/SAT/prove), pyswisseph (ephemeris) ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out |
| `astrology` | คำนวณดวงเต็มระบบจากวันเกิดเดียว: BaZi (สี่เสา), Western tropical, Vedic sidereal (Lahiri), Human Design + ชั้นอ่านคำทำนายภาษาไทย |
| `skill-maker` | scaffold สกิลใหม่ให้เป็น workflow — สร้าง `SKILL.md` + `scripts/run.py` (engine) + `references/notes.md` พร้อมโครง |
| `agent-loop` | บังคับงานผ่าน 7 เฟส (bootstrap_agent → perceive → goal_contract → policy_check → capability_discovery → plan → execute_loop) ด้วย state machine + gate + audit trail (`scripts/run.py`) |

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

## Dependency

```sh
pip install sympy z3-solver pyswisseph
```

- `math` ต้องมี `sympy` + `z3-solver`; ส่วน ephemeris ต้องมี `pyswisseph`
- `astrology` ต้องมี `pyswisseph` (แนบ `assets/*.se1` ซึ่งเป็น Swiss Ephemeris data มาให้แล้ว)
- `astro.ts` เป็น engine สำรองแบบ zero-dependency ต้องรันด้วย `npx tsx` (ความแม่นต่ำกว่า Python)

## ใช้งานเร็ว

```sh
# math
python skills/math/scripts/run.py '{"op":"solve","eq":"x**2 - 5*x + 6 = 0","symbol":"x"}'

# astrology (year month day hour minute lat lon tz)
python skills/astrology/scripts/astrology.py 1992 8 8 16 49 6.53995 101.29 7
python skills/astrology/scripts/reading.py 1992 8 8 16 49 6.53995 101.29 7 m
```
