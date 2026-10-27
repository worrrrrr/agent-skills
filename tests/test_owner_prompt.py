# tests/test_owner_prompt.py
"""ทดสอบ owner.prompt.md — prompt เดียวต้องมีกฎครบและพกพาได้

รันจาก repo root:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "owner.prompt.md"

REQUIRED = [
    "slot", "scope", "base rate", "stock", "flow",
    "E1", "E5", "minimal diff", "log", "learn", "timebox",
    "deterministic", "path:line",
]
EMOJI_RANGES = [(0x1F300, 0x1FAFF), (0x1F000, 0x1F2FF), (0x2600, 0x27BF), (0x2B00, 0x2BFF)]


class TestOwnerPrompt(unittest.TestCase):
    def setUp(self):
        self.text = PROMPT.read_text(encoding="utf-8")

    def test_exists_and_substantial(self):
        self.assertTrue(PROMPT.exists())
        self.assertGreater(len(self.text), 2500, "prompt สั้นเกินกว่าจะครอบกฎ")

    def test_covers_required_rules(self):
        missing = [k for k in REQUIRED if k.lower() not in self.text.lower()]
        self.assertEqual(missing, [], f"ขาดกฎ: {missing}")

    def test_no_emoji(self):
        bad = [ch for ch in self.text
               if any(lo <= ord(ch) <= hi for lo, hi in EMOJI_RANGES)
               and unicodedata.category(ch) == "So"]
        self.assertEqual(bad, [])

    def test_no_foreign_script_leak(self):
        bad = [ch for ch in self.text if 0x3000 <= ord(ch) <= 0x9FFF or 0x0400 <= ord(ch) <= 0x04FF]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
