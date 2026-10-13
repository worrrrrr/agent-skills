#!/usr/bin/env python3
"""Deterministic engine for skill: qa.

รัน test/lint/build จริงแล้วสรุปผลเป็น JSON: exit code ต่อคำสั่ง, จำนวนเทสต์
ที่ผ่าน/พัง (parse จาก summary ของ pytest/jest/vitest/go/unittest), เวลาที่ใช้,
และความล้มเหลว — ให้ supervisor ใช้เป็นหลักฐานตรวจงาน

Usage:
  python scripts/run.py '{"commands": ["python -m pytest -q"]}'

Input schema:
  commands  list  required — 1..20 คำสั่ง รับเป็น string หรือ
            {"cmd": "...", "name": "...", "timeout": 120}
  dir       string optional — working directory (ต้องมีอยู่จริง, default = cwd)
  timeout   number optional — timeout ต่อคำสั่ง วินาที (default 120, max 600)

Exit codes: 0 = engine รันครบ (อ่าน `verdict`) / 1 = input ไม่ครบ / 2 = JSON ผิดรูปแบบ
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

MAX_COMMANDS = 20
DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 600
TAIL_LIMIT = 2000

# summary patterns seen across runners (searched over captured output)
PATTERNS = [
    ("passed", r"(\d+) passed"),
    ("failed", r"(\d+) failed"),
    ("errors", r"(\d+) error(?:s)?"),
    ("skipped", r"(\d+) skipped"),
    ("total", r"(\d+) total"),
    ("ok", r"^OK$", "multiline"),
    ("unittest_failed", r"^FAILED \(.*\)", "multiline"),
]


def fail(message: str) -> None:
    print(json.dumps({"ok": False, "skill": "qa", "error": message},
                     ensure_ascii=False, indent=2))
    sys.exit(1)


def build_command(raw, index: int) -> dict:
    if isinstance(raw, str):
        cmd, name, timeout = raw.strip(), None, None
    elif isinstance(raw, dict):
        cmd = str(raw.get("cmd", "")).strip()
        name = str(raw.get("name", "")).strip() or None
        timeout = raw.get("timeout")
    else:
        fail(f"commands[{index}]: must be a string or an object")
    if not cmd:
        fail(f"commands[{index}]: missing 'cmd'")
    if timeout is not None and (isinstance(timeout, bool)
                                or not isinstance(timeout, (int, float))
                                or not 1 <= timeout <= MAX_TIMEOUT):
        fail(f"commands[{index}].timeout: must be 1..{MAX_TIMEOUT} seconds")
    return {"cmd": cmd, "name": name or cmd, "timeout": timeout}


def parse_summary(output: str) -> dict:
    """Extract test counts from known runner summary lines. None-safe."""
    found = {}
    for key, pattern, *rest in PATTERNS:
        flags = re.MULTILINE if rest else 0
        m = re.search(pattern, output, flags)
        if m:
            found[key] = 0 if m.groups() == () else int(m.group(1))
    # "OK" / "FAILED (...)" mean unittest ran: map to counts
    if "unittest_failed" in found:
        found.setdefault("failed", 1)
        found.pop("unittest_failed")
    if "ok" in found:
        found.setdefault("passed", 1)
        found.pop("ok")
    return found or None


def tail(text: str) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    joined = "\n".join(lines[-5:])
    return joined[-TAIL_LIMIT:]


def kill_tree(proc) -> None:
    """Kill the whole process tree — killing only the shell leaves the
    real work process holding the pipe, so communicate() never returns."""
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        except OSError:
            proc.kill()
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            proc.kill()


def run_one(spec: dict, workdir: str, default_timeout: int) -> dict:
    timeout = spec["timeout"] or default_timeout
    started = time.monotonic()
    timed_out = False
    output, exit_code = "", None
    try:
        proc = subprocess.Popen(
            spec["cmd"], shell=True, cwd=workdir,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace",
            start_new_session=(sys.platform != "win32"),
        )
        try:
            output, _ = proc.communicate(timeout=timeout)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_tree(proc)
            try:
                output, _ = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                output = ""
            exit_code = proc.returncode
    except OSError as e:
        output = f"engine error: {e}"
    output = output or ""
    duration_ms = round((time.monotonic() - started) * 1000)
    parsed = parse_summary(output) if output else None
    return {
        "name": spec["name"],
        "cmd": spec["cmd"],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "summary": parsed,
        "output_tail": tail(output) if output else "",
    }


def run(payload: dict) -> dict:
    if not isinstance(payload, dict):
        fail("input must be a JSON object")
    raw_commands = payload.get("commands")
    if not isinstance(raw_commands, list) or not raw_commands:
        fail("'commands' is required and must be a non-empty list")
    if len(raw_commands) > MAX_COMMANDS:
        fail(f"'commands' accepts at most {MAX_COMMANDS} items")
    workdir = payload.get("dir", ".")
    if not isinstance(workdir, str):
        fail("'dir' must be a string")
    if not os.path.isdir(workdir):
        fail(f"'dir' does not exist: {workdir}")
    default_timeout = payload.get("timeout", DEFAULT_TIMEOUT)
    if (isinstance(default_timeout, bool)
            or not isinstance(default_timeout, (int, float))
            or not 1 <= default_timeout <= MAX_TIMEOUT):
        fail(f"'timeout' must be 1..{MAX_TIMEOUT} seconds")

    commands = [build_command(c, i) for i, c in enumerate(raw_commands)]
    results = [run_one(c, workdir, default_timeout) for c in commands]
    ok_results = [r for r in results
                  if r["exit_code"] == 0 and not r["timed_out"]]
    failed_results = [r for r in results if r not in ok_results]

    tests_passed = sum(r["summary"].get("passed", 0)
                       for r in results if r["summary"])
    tests_failed = sum((r["summary"] or {}).get("failed", 0)
                       + (r["summary"] or {}).get("errors", 0)
                       for r in results)

    return {
        "ok": True,
        "skill": "qa",
        "verdict": "pass" if not failed_results else "fail",
        "dir": workdir,
        "results": results,
        "totals": {
            "commands": len(results),
            "commands_passed": len(ok_results),
            "commands_failed": len(failed_results),
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
        },
        "failures": [{"name": r["name"], "exit_code": r["exit_code"],
                      "timed_out": r["timed_out"], "tail": r["output_tail"]}
                     for r in failed_results],
        "next_actions": [
            (f"คำสั่ง timeout: {r['name']}" if r["timed_out"]
             else f"คำสั่งพัง (exit {r['exit_code']}): {r['name']}")
            for r in failed_results
        ],
    }


def main() -> None:
    raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"invalid JSON input: {e}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(run(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
