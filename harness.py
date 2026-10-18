#!/usr/bin/env python3
"""Task harness — run checks, write a report, and exit with the verdict.

    python harness.py '{"op":"run","task":"...","prompt":"...","checks":[
        {"id":"readme","cmd":"python check.py"},
        {"id":"math","skill":"math"}]}'
    python harness.py '{"op":"status","run":"<id>"}'
    python harness.py '{"op":"list"}'

The report is the result: `.harness/<run>/report.json` + report.md.
Verdict is derived from exit codes, never from prose.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TIMEOUT = 120
RUN_ID = re.compile(r"[A-Za-z0-9._-]{1,120}\Z")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def as_text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def slug(text: str, limit: int = 32) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return clean[:limit].strip("-") or "run"


def base_dir(payload: dict) -> Path:
    raw = as_text(payload.get("dir")) or "."
    return Path(raw).resolve()


def store(base: Path) -> Path:
    return base / ".harness"


def find_skill(base: Path, name: str) -> Path:
    for root in (base / "skills", Path.home() / ".agents" / "skills"):
        candidate = root / name
        if (candidate / "SKILL.md").is_file():
            return candidate
    raise ValueError("unknown skill: " + name)


def skill_smoke(base: Path, name: str):
    """Read the `smoke:` command a skill declares next to itself."""
    directory = find_skill(base, name)
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise ValueError("skill has no frontmatter: " + name)
    smoke = re.search(r"^smoke:\s*(.+)$", match.group(1), re.M)
    if not smoke:
        raise ValueError("skill has no smoke: command: " + name)
    return directory, smoke.group(1).strip()


def agent_loop_check(base: Path, run_id: str):
    """Treat an agent-loop run as a check: done + open=[] + verified=true."""
    engine = Path.home() / ".agents" / "skills" / "agent-loop" / "scripts" / "run.py"
    if not engine.is_file():
        return False, {"error": "agent-loop engine not found", "engine": str(engine)}
    payload = {"op": "status", "run": run_id, "dir": str(base)}
    try:
        proc = subprocess.run([sys.executable, str(engine), json.dumps(payload)],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        return False, {"error": str(error)}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, {"error": "invalid engine output",
                       "out": (proc.stdout or proc.stderr)[-1000:]}
    ok = (data.get("ok") is True and data.get("phase") == "done"
          and data.get("open") == [] and data.get("verified") is True)
    return ok, data


def run_one(base: Path, check: dict) -> dict:
    cid = as_text(check.get("id")) or as_text(check.get("skill")) or as_text(check.get("cmd"))
    if not cid:
        raise ValueError("each check needs id, cmd or skill")
    loop_run = as_text(check.get("agent_loop_run"))
    if loop_run:
        started = time.monotonic()
        ok, data = agent_loop_check(base, loop_run)
        return {
            "id": cid,
            "cmd": "agent-loop status " + loop_run,
            "cwd": str(base),
            "exit": 0 if ok else 1,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timed_out": False,
            "out": json.dumps(data, ensure_ascii=False)[-4000:],
        }

    skill = as_text(check.get("skill"))
    if skill:
        cwd, cmd = skill_smoke(base, skill)
        # A skill owns its smoke string; parse it without a shell so quotes work.
        args, use_shell = shlex.split(cmd, posix=True), False
    else:
        cmd = as_text(check.get("cmd"))
        raw_cwd = as_text(check.get("cwd"))
        cwd = (base / raw_cwd).resolve() if raw_cwd else base
        args, use_shell = cmd, True
    if not cmd:
        raise ValueError("check has no command: " + cid)
    try:
        timeout = max(1, min(int(check.get("timeout", DEFAULT_TIMEOUT)), 1800))
    except (TypeError, ValueError):
        raise ValueError("timeout must be an integer: " + cid)

    started = time.monotonic()
    try:
        proc = subprocess.run(args, shell=use_shell, cwd=str(cwd), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout)
        code = proc.returncode
        out = ((proc.stdout or "") + (proc.stderr or ""))[-4000:]
        timed_out = False
    except subprocess.TimeoutExpired:
        code, out, timed_out = 124, "timeout after %ss" % timeout, True
    return {
        "id": cid,
        "cmd": cmd,
        "cwd": str(cwd),
        "exit": code,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "timed_out": timed_out,
        "out": out,
    }


def write_report(directory: Path, report: dict) -> None:
    tmp = directory / "report.json.tmp"
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, directory / "report.json")
    lines = [
        "# Harness report: " + report["task"],
        "",
        "- run: `%s`" % report["id"],
        "- verdict: **%s**" % report["verdict"],
        "- started: %s · finished: %s" % (report["started"], report["finished"]),
        "",
        "| check | exit | ms |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append("| `%s` | %s | %s |" % (check["id"], check["exit"], check["duration_ms"]))
    if report["gaps"]:
        lines += ["", "## Gaps", ""] + ["- " + gap for gap in report["gaps"]]
    if report["prompt"]:
        lines += ["", "## Prompt", "", report["prompt"]]
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def op_run(payload: dict) -> dict:
    task = as_text(payload.get("task"))
    checks = payload.get("checks")
    if not task:
        return {"ok": False, "error": "run requires 'task'"}
    if not isinstance(checks, list) or not checks:
        return {"ok": False, "error": "run requires a non-empty 'checks' list"}
    base = base_dir(payload)
    if not base.is_dir():
        return {"ok": False, "error": "dir is not a directory: " + str(base)}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = stamp + "-" + os.urandom(2).hex() + "-" + slug(task)
    directory = store(base) / run_id
    directory.mkdir(parents=True, exist_ok=False)

    report = {
        "id": run_id,
        "task": task,
        "prompt": as_text(payload.get("prompt")),
        "started": utcnow(),
        "checks": [],
        "gaps": [],
    }
    for check in checks:
        try:
            result = run_one(base, check)
        except (ValueError, OSError) as error:
            report["checks"].append({"id": str(check), "cmd": "", "exit": 2,
                                     "duration_ms": 0, "timed_out": False,
                                     "out": str(error)})
            report["gaps"].append("invalid check: %s" % error)
            continue
        report["checks"].append(result)
        if result["exit"] != 0:
            report["gaps"].append("%s failed (exit %s)" % (result["id"], result["exit"]))

    report["finished"] = utcnow()
    report["verdict"] = "pass" if report["checks"] and not report["gaps"] else "fail"
    write_report(directory, report)
    return {"ok": True, "verdict": report["verdict"], "run": run_id,
            "report": str(directory / "report.json"), "gaps": report["gaps"]}


def op_status(payload: dict) -> dict:
    base = base_dir(payload)
    run_id = as_text(payload.get("run"))
    if not run_id:
        return op_list(payload)
    if not RUN_ID.fullmatch(run_id) or ".." in run_id:
        return {"ok": False, "error": "invalid run id: " + run_id}
    path = store(base) / run_id / "report.json"
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "error": "unknown run: " + run_id}
    return {"ok": True, **report}


def op_list(payload: dict) -> dict:
    base = base_dir(payload)
    directory = store(base)
    runs = []
    if directory.is_dir():
        for path in sorted(directory.iterdir(), reverse=True):
            report = path / "report.json"
            if not report.is_file():
                continue
            try:
                data = json.loads(report.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            runs.append({"run": path.name, "verdict": data.get("verdict"),
                         "task": data.get("task")})
    return {"ok": True, "runs": runs}


def smoke_skills(base: Path) -> list:
    checks = []
    for directory in sorted((base / "skills").glob("*")):
        md = directory / "SKILL.md"
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if match and re.search(r"^smoke:\s*.+$", match.group(1), re.M):
            checks.append({"id": directory.name, "skill": directory.name})
    return checks


def selfcheck(base: Path) -> dict:
    checks = [{"id": "repo", "cmd": "python check.py"}] + smoke_skills(base)
    return op_run({"task": "selfcheck", "dir": str(base), "checks": checks})


OPS = {"run": op_run, "status": op_status, "list": op_list}


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--selfcheck":
        base = Path(__file__).resolve().parent
        result = selfcheck(base)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result.get("verdict") == "pass" else 1)
    raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        print(json.dumps({"ok": False, "error": "invalid JSON: %s" % error},
                         ensure_ascii=False))
        sys.exit(2)
    if not isinstance(payload, dict):
        print(json.dumps({"ok": False, "error": "payload must be a JSON object"}))
        sys.exit(2)
    op = as_text(payload.get("op"))
    if op not in OPS:
        print(json.dumps({"ok": False, "error": "unknown op: %s" % op}))
        sys.exit(2)
    result = OPS[op](payload)
    print(json.dumps(result, ensure_ascii=False))
    if not result.get("ok"):
        sys.exit(2)
    sys.exit(0 if result.get("verdict", "pass") == "pass" else 1)


if __name__ == "__main__":
    main()
