# agent-skills

ชุด Agent Skills สำหรับงานคำนวณแบบ exact/symbolic และโหราศาสตร์เต็มระบบ
ใช้ได้กับ agent ที่รองรับ Agent Skills (OpenCode, Claude Code, Codex, Cursor, ...)

## Skills

| Skill | ทำอะไร |
| --- | --- |
| `math` | เครื่องคำนวณ exact — calc, sympy (สมการ/calculus/matrix), z3 (constraint/SAT/prove), pyswisseph (ephemeris) ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out |
| `astrology` | คำนวณดวงเต็มระบบจากวันเกิดเดียว: BaZi (สี่เสา), Western tropical, Vedic sidereal (Lahiri), Human Design + ชั้นอ่านคำทำนายภาษาไทย |
| `qa` | รัน test/lint/build จริงแล้วสรุปผลเป็น JSON — เก็บ exit code, จำนวนเทสต์ผ่าน/พัง (parse summary ของ pytest/jest/go/unittest), เวลา และ output tail ผ่าน `scripts/run.py` ให้ `supervisor` ใช้เป็นหลักฐานตรวจงาน |
| `supervisor` | ตรวจงาน + ให้คะแนนแบบหัวหน้างาน — รับชิ้นงาน + เกณฑ์ acceptance แล้ว engine ตรวจ keyword coverage, ให้คะแนน/เกรด, ชี้ gaps + next_actions ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out |
| `skill-maker` | scaffold สกิลใหม่ให้เป็น workflow — สร้าง `SKILL.md` + `scripts/run.py` (engine) + `references/notes.md` พร้อมโครง |
| `agent-loop` | บังคับงานผ่าน 7 เฟส (bootstrap_agent → perceive → goal_contract → policy_check → capability_discovery → plan → execute_loop) ด้วย state machine + gate + audit trail (`scripts/run.py`) |
| `skillcheck` | ตรวจสุขภาพชุดสกิลแบบรันเองได้ — ค้น skill ทั้งหมด ตรวจโครงสร้าง/หน้า registry แล้ว smoke-run engine แต่ละตัวด้วย payload ว่าง บอกว่าตัวไหนใช้ได้จริงในเครื่องนี้ + dependency ที่ขาด ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out |
| `linkcheck` | ตรวจลิงก์/ไฟล์อ้างอิงที่พังในเอกสาร — สแกน Markdown ทั้ง repo (README, docs, SKILL.md) แล้วตรวจ relative link, anchor ใน .md และ path ใน backtick ว่าชี้ถึงไฟล์จริง พร้อมตัวเลือกเช็ค http link ภายนอก ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out |
| `knowledge` | สร้าง/รักษาฐานความรู้โปรเจกต์ให้ถูกต้องอัพเดท — สกัดข้อเท็จจริงจากไฟล์จริง (manifest, commands, สกิล, git, env keys) เขียนเป็น KNOWLEDGE.md พร้อม fingerprint ให้ verify ตรวจ freshness ได้ ใช้ก่อนเริ่มเขียนโค้ด ผ่าน `scripts/run.py` แบบ JSON-in/JSON-out |

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

# skillcheck — เช็คสุขภาพสกิลทั้งชุด (รันเองได้ ไม่ต้อง input)
python skills/skillcheck/scripts/run.py '{}'

# linkcheck — ตรวจลิงก์/ไฟล์อ้างอิงที่พังในเอกสารทั้ง repo
python skills/linkcheck/scripts/run.py '{}'

# knowledge — สกัดข้อเท็จจริงโปรเจกต์ / เขียน KNOWLEDGE.md / ตรวจ freshness
python skills/knowledge/scripts/run.py '{"op": "build"}'
```
