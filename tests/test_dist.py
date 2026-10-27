# tests/test_dist.py
"""ทดสอบ dist zip: แตกไฟล์แจกจ่ายแล้วต้องติดตั้ง/รันได้จริง

รันจาก repo root:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def latest_zip() -> Path | None:
    zips = sorted(DIST.glob("agent-skills-*.zip"))
    return zips[-1] if zips else None


def frontmatter_smoke(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("smoke:"):
            return line.split(":", 1)[1].strip()
    return None


class TestDistPackage(unittest.TestCase):
    def setUp(self):
        self.zip_path = latest_zip()
        if self.zip_path is None:
            self.skipTest("ยังไม่มี dist/*.zip — รัน python scripts/build_dist.py ก่อน")

    def test_manifest_matches_archive(self):
        with zipfile.ZipFile(self.zip_path) as zf:
            manifest = json.loads(zf.read("MANIFEST.json").decode("utf-8"))
            names = set(zf.namelist())
        for entry in manifest["files"]:
            self.assertIn(entry["path"], names, f"missing in zip: {entry['path']}")
        self.assertIn("owner.prompt.md", names)

    def test_extracted_skills_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(self.zip_path) as zf:
                zf.extractall(tmp)
            root = Path(tmp)
            self.assertTrue((root / "owner.prompt.md").exists())
            skills = [p for p in (root / "skills").iterdir() if p.is_dir()]
            self.assertGreaterEqual(len(skills), 4)
            checked = 0
            for skill in skills:
                smoke = frontmatter_smoke(skill / "SKILL.md")
                if not smoke:
                    continue
                cmd = shlex.split(smoke)
                if cmd[0] == "python":
                    cmd[0] = sys.executable
                proc = subprocess.run(cmd, cwd=skill, capture_output=True, text=True, timeout=60)
                self.assertEqual(proc.returncode, 0,
                                 f"{skill.name}: smoke failed: {proc.stderr[:200]}")
                checked += 1
            self.assertGreaterEqual(checked, 3, "ต้องมี skill ที่มี smoke อย่างน้อย 3 ตัว")


if __name__ == "__main__":
    unittest.main()
