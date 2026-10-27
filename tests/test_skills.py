"""Self-tests for the skill set (no deps, run from repo root).

Three test groups:
  TestStructure  — frontmatter, description trigger, body length, dangling refs
  TestLeakage    — emoji / CJK / Cyrillic leakage in the Thai doctrine skills
  TestReadability— line length, headings, worked examples per skill
  TestCoverage   — every known hard case is encoded by at least one skill

Run: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import re
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NEW_SKILLS = {"slot-audit", "frame-ask", "evidence-class"}
REF_RE = re.compile(r"`(scripts|references|assets)/([^`]+)`")
EMOJI_RANGES = [
    (0x1F300, 0x1FAFF), (0x1F000, 0x1F2FF), (0x2600, 0x27BF),
    (0x2B00, 0x2BFF), (0xFE0F, 0xFE0F), (0x1F1E6, 0x1F1FF),
]


def parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    front = text[3:end]
    body = text[end + 4:]
    meta = {}
    for line in front.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()
    return meta, body


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


class TestStructure(unittest.TestCase):
    def test_name_matches_folder(self):
        for d in skill_dirs():
            meta, _ = parse(d / "SKILL.md")
            self.assertEqual(meta.get("name"), d.name, f"{d.name}: name mismatch")

    def test_description_has_use_when(self):
        for d in skill_dirs():
            meta, _ = parse(d / "SKILL.md")
            self.assertIn("Use when", meta.get("description", ""), f"{d.name}: missing 'Use when'")

    def test_body_long_enough(self):
        for d in skill_dirs():
            _, body = parse(d / "SKILL.md")
            self.assertGreater(len(body.strip()), 300, f"{d.name}: body too short")

    def test_no_dangling_refs(self):
        for d in skill_dirs():
            _, body = parse(d / "SKILL.md")
            for folder, rest in REF_RE.findall(body):
                name = rest.split()[0]
                if "*" in name:
                    continue  # glob pattern, not a single file
                target = d / folder / name
                self.assertTrue(target.exists(), f"{d.name}: dangling ref {folder}/{name}")


class TestLeakage(unittest.TestCase):
    def test_no_emoji(self):
        for d in skill_dirs():
            _, body = parse(d / "SKILL.md")
            bad = [ch for ch in body
                   if any(lo <= ord(ch) <= hi for lo, hi in EMOJI_RANGES)
                   and unicodedata.category(ch) == "So"]
            self.assertEqual(bad, [], f"{d.name}: emoji found {bad}")

    def test_no_cjk_or_cyrillic_in_new_skills(self):
        for name in NEW_SKILLS:
            _, body = parse(SKILLS / name / "SKILL.md")
            bad = [ch for ch in body if 0x3000 <= ord(ch) <= 0x9FFF or 0x0400 <= ord(ch) <= 0x04FF]
            self.assertEqual(bad, [], f"{name}: leaked non-Thai script {bad}")


class TestReadability(unittest.TestCase):
    def test_line_length(self):
        for name in NEW_SKILLS:
            _, body = parse(SKILLS / name / "SKILL.md")
            long_lines = [(i + 1, len(l)) for i, l in enumerate(body.splitlines()) if len(l) > 260]
            self.assertEqual(long_lines, [], f"{name}: lines too long {long_lines}")

    def test_has_structure(self):
        for name in NEW_SKILLS:
            _, body = parse(SKILLS / name / "SKILL.md")
            headings = re.findall(r"^##+ .+$", body, flags=re.M)
            self.assertGreaterEqual(len(headings), 3, f"{name}: needs >=3 headings")
            self.assertRegex(body, r"ตัวอย่าง|ขั้นตอน|กติกา", f"{name}: missing procedure or example section")
            self.assertGreaterEqual(body.count("|"), 8, f"{name}: expected a table with content")


class TestCoverage(unittest.TestCase):
    def test_every_case_is_encoded(self):
        cases = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))
        for c in cases:
            path = SKILLS / c["skill"] / "SKILL.md"
            self.assertTrue(path.exists(), f"{c['id']}: skill {c['skill']} missing")
            body = path.read_text(encoding="utf-8")
            hit = any(k in body for k in c["keywords"])
            self.assertTrue(hit, f"{c['id']}: keywords {c['keywords']} not found in {c['skill']}")


if __name__ == "__main__":
    unittest.main()
