# UI/UX Spec — Agent Skills Hub

เวอร์ชัน 1.0 · เขียนเพื่อสร้างแอปจริง (ไม่ใช่หน้า docs นิ่ง) · สไตล์อ้างอิง shadcn/ui

---

## 1. ภาพรวมผลิตภัณฑ์

**Agent Skills Hub** คือเว็บแอปสำหรับชุดสกิลใน repo นี้ — ให้ผู้ใช้เรียกดู ค้นหา และ**รันสกิลได้จริง** (engine รับ JSON เห็นผลลัพธ์จริง) แทนการอ่าน SKILL.md อย่างเดียว

**เป้าหมาย (v1)**
1. เรียกดูสกิลทั้งหมดพร้อมคำอธิบาย ตัวอย่างคำสั่ง และคัดลอก input ตัวอย่างได้ในคลิกเดียว
2. รัน demo ของ engine แต่ละสกิลจากหน้าเว็บ แล้วเห็น JSON ผลลัพธ์จริง
3. ใช้งานได้ลื่นบนมือถือและ desktop, ธีมสว่าง/มืด

**Non-goals (v1)**
- ไม่ใช่ code editor / IDE และไม่เก็บผลรันถาวร
- ไม่ทำ auth, multi-user, billing
- ไม่แทนที่ CLI — แอปคือ "หน้าต่าง" ให้เห็นสิ่งที่ CLI ทำได้

**Persona**
- **ผู้ใช้หลัก**: developer ที่ใช้ agent (OpenCode/Claude Code/Cursor) อยากรู้ว่าสกิลไหนทำอะไร ใช้กับ agent ตัวเองยังไง — เข้าถึงบ่อย อยากรวยเร็ว ชอบ copy-paste
- **ผู้ใช้รอง**: คนทั่วไปที่อยากลอง "ดวงเกิด" หรือ "แก้สมการ" ผ่านหน้าเว็บโดยไม่รู้ CLI

---

## 2. Design Foundation (shadcn/ui)

**สแต็ก**: React 19 + Vite (หรือ Next.js) · Tailwind CSS v4 (`@theme` ใน CSS ไม่ใช่ config.js) · shadcn/ui สไตล์ **new-york v4** · Radix primitives · สีเป็น **OKLCH** ผ่าน CSS variables

**Design tokens** (ตั้งใน `globals.css` ด้วย `@theme inline` — semantic ห้าม hardcode สีในคอมโพเนนต์)

| Token | หน้าที่ | ค่าเริ่มต้น (light / dark) |
| --- | --- | --- |
| `--background` / `--foreground` | พื้นหลังหลัก | `oklch(1 0 0)` / `oklch(0.145 0 0)` |
| `--card` / `--card-foreground` | การ์ด | ขาวนวล / เทาเข้ม |
| `--primary` / `--primary-foreground` | ปุ่มหลัก, accent | น้ำเงินเข้ม `oklch(0.21 0.034 265)` / white |
| `--muted` / `--muted-foreground` | ข้อความรอง, พื้นที่ว่าง | เทาอ่อน |
| `--border`, `--input`, `--ring` | เส้นขอบ, ช่อง input, focus ring | เทา 200/800 |
| `--radius` | มุมโค้งทั้งระบบ | `0.75rem` (โค้งกว่า default ของ shadcn เล็กน้อย ให้ดูทันสมัยขึ้น) |
| `--success`, `--warning`, `--destructive` | สถานะผลลัพธ์ (pass/fail) | เขียว/เหลือง/แดง OKLCH |

**Typography**
- UI: `--font-sans` = **IBM Plex Sans Thai** (หรือ Noto Sans Thai) + fallback `system-ui` — ต้องครอบคลุมสระ/วรรณยุกต์เต็ม ไม่ตัดน้ำหนักไทยกลางคัน
- โค้ด/JSON: `--font-mono` = JetBrains Mono / Geist Mono
- สเกล: heading h1 `text-2xl/700`, h2 `text-lg/600`, body `text-sm` (dense) — สไตล์ dashboard ไม่ใช่ blog

**Density**: ระยะห่างแบบ compact — padding การ์ด `p-4`, gap ตาราง `gap-2`, ตั้ง `--radius` ให้ทุก component ใช้ร่วมกัน

**รูปแบบที่ต้องเป็น shadcn จริง**: ใช้คอมโพเนนต์จาก registry (`npx shadcn add card button badge tabs dialog table input textarea sonner skeleton alert dropdown-menu tooltip`) — ห้ามเขียน component พื้นฐานเอง; สไตล์ปรับผ่าน token เท่านั้น

---

## 3. Information Architecture

```
/                     Landing: hero + ตารางสกิล (cards) + สถิติ
/skills               รายการสกิลทั้งหมด + ค้นหา/กรอง
/skills/[slug]        หน้าสกิล: คำอธิบาย, ตัวอย่าง, playground
/skills/[slug]#demo   (anchor) แผงรัน demo — เห็น JSON output จริง
/runs                 ประวัติรันล่าสุดในเครื่อง (localStorage, v1)
/settings             ธีม (light/dark/system), ค่าทั่วไป
```

Navigation: sidebar คงที่บน desktop (ไอคอน + ชื่อสกิล), bottom bar 4 แท็บบนมือถือ

---

## 4. Screen Specs

### 4.1 Landing `/`

- **Hero**: ชื่อ "Agent Skills Hub" + คำอธิบายบรรทัดเดียว + ปุ่ม `เริ่มใช้งาน` (ไป `/skills`) และ `ดูวิธีติดตั้ง` (Dialog แสดง `npx skills add …` + ปุ่ม copy)
- **StatStrip**: จำนวนสกิล, จำนวน engine ops รวม, dependency ที่ต้องใช้ — ดึงจาก metadata ไม่ hardcode
- **SkillGrid**: การ์ดสกิล (Card + Badge แสดง trigger keywords 3 คำแรก) — คลิกเข้า `/skills/[slug]`
- **สถานะ**: skeleton grid ขณะโหลด; Empty/Error state พร้อมปุ่ม retry

### 4.2 รายการสกิล `/skills`

- **SearchInput** (ค้นชื่อ + คำอธิบาย + triggers) + **FilterChips** (หมวด: คำนวณ/ดวง/งาน/อื่นๆ) + เรียงตามชื่อ
- ตาราง (Table) บน desktop: ชื่อสกิล | ทำอะไร | triggers | คำสั่งติดตั้ง (มีปุ่ม copy ระดับ cell) — การ์ดซ้อนกันบนมือถือ
- ผลค้นหาว่าง → Empty state "ไม่พบสกิลที่ตรงกับ '<query>'" พร้อมปุ่มล้างตัวกรอง

### 4.3 หน้าสกิล `/skills/[slug]` — หัวใจของแอป

Layout สองคอลัมน์บน desktop (1 คอลัมน์มือถือ):

**คอลัมน์ซ้าย — เอกสาร**
1. Header: ชื่อสกิล + Badge "engine" + ปุ่ม `คัดลอกคำสั่งติดตั้ง`
2. Tabs: `ภาพรวม` | `Inputs` | `ตัวอย่าง` | `กติกา (notes)`
   - **Inputs**: ตาราง field/type/required จาก SKILL.md — แปลงเป็น schema อัตโนมัติ
   - **ตัวอย่าง**: code block พร้อมปุ่ม `ส่งเข้า playground` (เติม payload ลงแผงขวาอัตโนมัติ)
   - **กติกา**: render `references/*.md` ถ้าสกิลมี

**คอลัมน์ขวา — Playground**
- **PayloadEditor**: Textarea (JSON, monospace) + ตรวจ JSON syntax ทันที (เส้นขอบแดง + ข้อความใต้ช่องเมื่อเพี้ยน) + ปุ่ม `รัน` (Primary)
- **ResultPanel** ใต้ editor:
  - แถบสถานะ: `verdict` เป็น Badge สี (pass=success, fail=destructive) + `duration_ms`
  - `pre` JSON output พร้อมปุ่ม copy; ถ้า result มี `coverage`/`verdict` ให้สรุปเป็น stat chips จาก field ที่มีจริง
  - `output_tail` หรือ `next_actions` แสดงเป็น Alert destructive เมื่อ fail
- **สถานะ**: ปุ่มรัน = Spinner + disabled; error ของ engine → Alert พร้อม stderr; timeout → เตือน "อาจค้าง — ลองลด timeout"
- **ความปลอดภัย**: payload ที่รันได้ถูกจำกัด whitelist ต่อสกิล (v1: รันผ่าน allowlist ของ demo payload เท่านั้น ไม่รับคำสั่งเสรีจากเว็บ)

### 4.4 ประวัติรัน `/runs`

- Table: เวลา | สกิล | verdict | duration | ปุ่ม `เปิดซ้ำ` (โหลด payload เดิมเข้าหน้าสกิล)
- เก็บใน localStorage (v1) — มีปุ่ม `ล้างประวัติ` ใน DropdownMenu พร้อมยืนยันผ่าน AlertDialog

### 4.5 ตั้งค่า `/settings`

- **ThemeSelector**: Light / Dark / System ( segmented control) — เขียน `data-theme` ลง `<html>`
- ข้อมูลเวอร์ชันสกิล/commit ของ repo

---

## 5. Responsive

| Breakpoint | พฤติกรรม |
| --- | --- |
| `< 640px` | 1 คอลัมน์, sidebar → bottom bar, playground อยู่ล่างสุด sticky bar มีปุ่ม `รัน` |
| `640–1024px` | ตารางเปลี่ยนเป็นการ์ด, สองคอลัมน์เริ่มใช้ได้ |
| `> 1024px` | sidebar + 2 คอลัมน์เต็ม, max-width รวม `max-w-6xl` กลางจอ |

ทัช target ≥ 44px บนมือถือ; ปุ่ม copy ไม่หดหายใน cell แคบ

---

## 6. Accessibility

- พื้นฐาน Radix ได้ ARIA มาให้ — ห้ามถอด `aria-*` ออก
- Focus ring ชัด (`--ring` + `focus-visible:ring-2`) ทุกปุ่ม/ลิงก์/input
- คอนทราสต์ข้อความผ่าน WCAG AA (4.5:1) ทั้งสองธีม — ตรวจด้วย token ไม่ใช่ตา
- แผงผลลัพธ์: แจ้งสถานะแก่ screen reader ด้วย `aria-live="polite"` เมื่อรันเสร็จ
- ตารางมี `<caption>`/`scope`; ปุ่มไอคอนต้องมี `aria-label`
- รองรับ `prefers-reduced-motion`

---

## 7. Motion

- จำกัดที่ 150–200 ms: hover การ์ด (`translate-y-[-2px]` + เงา), แสดง ResultPanel (fade+slide เล็กน้อย), Spinner ตอนรัน
- ไม่มี animation หนัก ๆ หรือ parallax — แอปเครื่องมือ ไม่ใช่ landing ขายของ

---

## 8. UX Writing (ไทย-first)

- ข้อความ UI เป็นภาษาไทย; ชื่อฟิลด์/ค่า JSON คงเป็นอังกฤษตามที่ engine คืน
- ปุ่มใช้คำกริยาสั้น ๆ: `รัน`, `คัดลอก`, `ส่งเข้า playground`, `ลองอีกครั้ง`
- ข้อความ error บอก "เกิดอะไร + ทำอะไรต่อ" เช่น "JSON เพี้ยนที่บรรทัด 3 — แก้แล้วกด รัน ใหม่"
- ห้ามใช้ศัพท์กำกวม: ไม่พูด "ผ่าน/ไม่ผ่าน" โดยไม่ระบุว่าเกณฑ์ไหน

---

## 9. Acceptance Criteria (ตรวจด้วยคำสั่ง/agent ที่มีใน repo)

1. `npx shadcn add` ครบทุกคอมโพเนนต์ที่อ้างในสเปก ไม่มีการเขียนปุ่ม/การ์ดเองซ้ำ
2. ทุกหน้ามี 4 สถานะ: loading (skeleton), empty, error (+retry), success
3. ธีม light/dark สลับได้ใน `/settings` และจำค่าได้หลัง refresh
4. ปุ่ม copy ทุกจุดคืนค่า `copied` feedback (เช่น check icon 1.5 วิ)
5. ค้นหาบน `/skills` กรองได้ทั้งชื่อและ triggers และมี empty state
6. Playground รัน demo payload ของทุกสกิลที่มี engine และแสดงผล JSON จริง (ไม่ใช่ mock)
7. ผ่าน Lighthouse: a11y ≥ 90, คอนทราสต์ AA ทั้งสองธีม
8. ทดสอบมือถือ 375px และ desktop 1440px ไม่มีส่วนหัก/เลื่อนแนวนอน (ยกเว้นใน `pre`)

---

## 10. ระยะถัดไป (นอกขอบ v1)

- บันทึกผลรันลง D1/R2 (ถ้าขึ้น hosting) + ประวัติข้ามเครื่อง
- share ลิงก์ payload (URL-encoded) ให้เพื่อนเปิดแล้วเห็นผลเดิม
- "รันทั้งชุด": รัน demo payload หลายตัวพร้อมกันในแท็บเดียว
- ติดตั้งสกิลจากเว็บ (เปิด `npx skills add` ด้วย deep link)
