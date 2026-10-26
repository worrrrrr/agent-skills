#!/usr/bin/env node
/**
 * spec-guard · thin npx wrapper
 *
 * มี engine เดียวเท่านั้น (scripts/run.py) — ไฟล์นี้ทำหน้าที่แปลง argv เป็น JSON
 * แล้วเรียก python ให้ จึงไม่มีการคำนวณซ้ำ และผลลัพธ์ตรงกับ skill ทุกประการ
 *
 *   npx spec-guard check C:/path/to/project
 *   npx spec-guard check . --today 2026-10-27
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const engine = path.join(here, "..", "scripts", "run.py");

const args = process.argv.slice(2);
const op = args[0] && !args[0].startsWith("-") ? args[0] : "check";
const target = args.find((a, i) => i > 0 && !a.startsWith("-")) || ".";
const todayIdx = args.indexOf("--today");
const today = todayIdx !== -1 ? args[todayIdx + 1] : undefined;

const payload = JSON.stringify({ op, target, ...(today ? { today } : {}) });
const python = process.platform === "win32" ? "python" : "python3";

for (const bin of [python, "python"]) {
  const res = spawnSync(bin, [engine, payload], { stdio: "inherit" });
  if (!res.error) process.exit(res.status ?? 1);
}

console.error(
  "spec-guard: ต้องมี python 3.10+ ในเครื่อง (engine อยู่ที่ scripts/run.py) — ติดตั้ง python หรือรัน engine ตรง ๆ"
);
process.exit(2);
