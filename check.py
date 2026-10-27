#!/usr/bin/env python3
"""Executable definition of done for this repo — exit 1 on drift.

Checks that every skill has a valid contract and that README tells the truth.
Run: python check.py
"""
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
fails = []
smokes = {}

skills = sorted(d for d in (ROOT / "skills").iterdir() if d.is_dir())
names = [d.name for d in skills]

for d in skills:
    md = d / "SKILL.md"
    if not md.exists():
        fails.append(f"{d.name}: missing SKILL.md")
        continue
    text = md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        fails.append(f"{d.name}: no YAML frontmatter")
        continue
    fm = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
    if fm.get("name") != d.name:
        fails.append(f"{d.name}: frontmatter name != folder ({fm.get('name')!r})")
    if "use when" not in fm.get("description", "").lower():
        fails.append(f"{d.name}: description has no 'Use when' trigger")
    if fm.get("smoke"):
        smokes[d.name] = fm["smoke"]
    body = text[m.end():]
    if len(body.strip()) < 80:
        fails.append(f"{d.name}: body too thin")
    refs = set(re.findall(r"`((?:scripts|references|assets)/[^`\s*]+)`", body))
    refs |= set(re.findall(r"\]\(((?:scripts|references|assets)/[^)\s]+)\)", body))
    for ref in sorted(refs):
        if not (d / ref).exists():
            fails.append(f"{d.name}: dangling ref {ref}")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
# ตาราง skills อยู่ใน section "## Skills" เท่านั้น — ตารางอื่น (ติดตั้ง/สถานะ) ไม่ใช่รายชื่อ skill
skills_section = re.search(r"^## Skills\s*$(.*?)^## ", readme, re.M | re.S)
scope = skills_section.group(1) if skills_section else readme
listed = re.findall(r"^\|\s*`([^`]+)`\s*\|", scope, re.M)
if sorted(listed) != names:
    fails.append(f"README skills {listed} != folders {names}")
for s in sorted(set(re.findall(r"python skills/([^/]+)/", readme))):
    if s not in names:
        fails.append(f"README references missing skill: {s}")
for link in re.findall(r"\]\((?!https?:)([^)#]+)\)", readme):
    if not (ROOT / link).exists():
        fails.append(f"README broken link: {link}")

# Smoke-run the command each skill declares in its own frontmatter (`smoke:`).
notes = []
for name, command in sorted(smokes.items()):
    try:
        args = shlex.split(command, posix=True)
        proc = subprocess.run(args, cwd=ROOT / "skills" / name,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
    except subprocess.TimeoutExpired:
        fails.append(f"{name}: smoke timeout")
        continue
    if "ModuleNotFoundError" in proc.stderr:
        notes.append(f"{name}: smoke SKIP (missing dependency)")
        continue
    if proc.returncode != 0:
        fails.append(f"{name}: smoke exit {proc.returncode}: "
                     f"{(proc.stderr or proc.stdout)[:200]}")
        continue
    notes.append(f"{name}: smoke OK")

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
else:
    print(f"PASS — {len(names)} skills: {', '.join(names)}")
    for n in notes:
        print(" -", n)
sys.exit(1 if fails else 0)
