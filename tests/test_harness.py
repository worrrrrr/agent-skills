"""Tests for harness.py (stdlib only)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "harness.py"


def call(payload: dict):
    proc = subprocess.run([sys.executable, str(HARNESS), json.dumps(payload)],
                          capture_output=True, text=True, encoding="utf-8")
    return json.loads(proc.stdout), proc.returncode


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_passing_checks_make_a_pass_report(self):
        out, code = call({"op": "run", "task": "ok", "dir": self.dir,
                          "checks": [{"id": "one", "cmd": 'python -c "print(1)"'}]})
        self.assertEqual(code, 0, out)
        self.assertEqual(out["verdict"], "pass")
        report = json.loads(Path(out["report"]).read_text(encoding="utf-8"))
        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(report["checks"][0]["exit"], 0)

    def test_failing_check_fails_the_report(self):
        out, code = call({"op": "run", "task": "fail", "dir": self.dir,
                          "checks": [{"id": "bad",
                                      "cmd": 'python -c "import sys; sys.exit(3)"'}]})
        self.assertEqual(code, 1)
        self.assertEqual(out["verdict"], "fail")
        self.assertTrue(out["gaps"])

    def test_skill_check_uses_its_own_smoke(self):
        skill = Path(self.dir) / "skills" / "demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo skill\n"
            'smoke: python -c "print(1)"\n---\n\nbody\n',
            encoding="utf-8")
        out, code = call({"op": "run", "task": "skill", "dir": self.dir,
                          "checks": [{"id": "demo", "skill": "demo"}]})
        self.assertEqual(code, 0, out)
        self.assertEqual(out["verdict"], "pass")

    def test_no_checks_is_an_error(self):
        out, code = call({"op": "run", "task": "empty", "dir": self.dir})
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])

    def test_agent_loop_run_must_be_done_and_verified(self):
        out, code = call({"op": "run", "task": "loop", "dir": self.dir,
                          "checks": [{"id": "loop",
                                      "agent_loop_run": "does-not-exist"}]})
        self.assertEqual(code, 1)
        self.assertEqual(out["verdict"], "fail")

    def test_status_reads_the_report(self):
        out, _ = call({"op": "run", "task": "ok", "dir": self.dir,
                       "checks": [{"id": "one", "cmd": 'python -c "print(1)"'}]})
        status, code = call({"op": "status", "run": out["run"], "dir": self.dir})
        self.assertEqual(code, 0)
        self.assertEqual(status["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
