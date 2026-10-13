#!/usr/bin/env python3
"""Deterministic engine for skill: skillcheck.

ตรวจสุขภาพชุดสกิลแบบรันเองได้ — ค้น skill ทุกตัวในโฟลเดอร์ ตรวจโครงสร้าง
(SKILL.md + frontmatter + scripts/) + บรรทัดใน README registry แล้ว smoke-run
engine แต่ละตัวด้วย payload ว่าง `{}` เพื่อจำแนกว่าตัวไหนใช้ได้จริงในสภาพ
แวดล้อมนี้ (accepts/rejects/ok) และตัวไหนพังจริง (missing_dependency/
invalid_output/crashed/timeout)

Usage:
  python scripts/run.py '{}'
  python scripts/run.py '{"only": ["math", "qa"]}'
  python scripts/run.py '{"dir": "../../..", "timeout": 30}'

Input schema:
  dir      string  optional — โฟลเดอร์ที่เก็บ skill
                   (default: ./skills ถ้ามี, ไม่งั้นใช้โฟลเดอร์ skills ที่สกิลนี้
                   ติดตั้งอยู่ — รันจากที่ไหนก็ได้โดยไม่ต้องระบุ)
  timeout  number  optional — timeout ต่อ engine วินาที (default 20, max 120)
  only     list    optional — เช็คเฉพาะสกิลชื่อเหล่านี้ (ชื่อโฟลเดอร์)

Smoke rules:
  - ถ้าหน้า SKILL.md ประกาศ `smoke: <คำสั่ง>` จะรันคำสั่งนั้น (cwd = โฟลเดอร์สกิล)
  - ไม่งั้น ถ้ามี `scripts/run.py` จะรัน `python run.py '{}'` (cwd = scripts/)
  - skillcheck ข้าม engine ของตัวเองเสมอ (กัน recursion)
  - สกิลที่ไม่มีทั้งคู่ → status "skipped" + คำแนะนำให้เพิ่ม `smoke:`

Exit codes: 0 = engine รันครบ (อ่าน `verdict`) / 1 = input ไม่ครบ / 2 = JSON ผิดรูปแบบ
"""
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_TIMEOUT = 20
MAX_TIMEOUT = 120
TAIL_LIMIT = 500

SELF_RUN = Path(__file__).resolve()

# module name -> pip package สำหรับ next_actions
PIP_NAMES = {
    "swisseph": "pyswisseph",
    "z3": "z3-solver",
    "yaml": "pyyaml",
    "PIL": "pillow",
}

HEALTHY_STATUSES = {"accepts", "rejects", "ok"}
UNHEALTHY_STATUSES = {"missing_dependency", "invalid_output", "crashed", "timeout"}


def fail(message: str) -> None:
    print(json.dumps({"ok": False, "skill": "skillcheck", "error": message},
                     ensure_ascii=False, indent=2))
    sys.exit(1)


def tail(text: str) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return "\n".join(lines[-5:])[-TAIL_LIMIT:]


def kill_tree(proc) -> None:
    """Kill the whole process tree — killing only the shell leaves the real
    work process holding the pipe, so communicate() never returns."""
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


def front_matter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def finding(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def smoke_spec(scripts_dir: Path, meta: dict) -> dict:
    """Pick how to smoke this skill: declared `smoke:` cmd > default run.py."""
    custom = meta.get("smoke", "")
    if custom:
        return {"kind": "custom", "command": custom, "shell": True,
                "cwd": scripts_dir.parent}
    if (scripts_dir / "run.py").is_file():
        return {"kind": "json", "command": "python run.py {}",
                "argv": [sys.executable, "run.py", "{}"], "shell": False,
                "cwd": scripts_dir}
    return {"kind": "none", "command": None}


def execute(spec: dict, timeout: int) -> dict:
    started = time.monotonic()
    out, err, rc, timed_out = "", "", None, False
    try:
        proc = subprocess.Popen(
            spec["argv"] if spec.get("argv") else spec["command"],
            shell=not spec.get("argv"),
            cwd=str(spec["cwd"]),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace",
            start_new_session=(sys.platform != "win32"),
        )
        try:
            out, err = proc.communicate(timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_tree(proc)
            try:
                out, err = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                out, err = "", ""
            rc = proc.returncode
    except OSError as e:
        err = f"engine error: {e}"
    return {
        "status_hint": None,
        "exit_code": rc,
        "timed_out": timed_out,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "stdout": out or "",
        "stderr": err or "",
    }


def classify(exec_result: dict, kind: str) -> dict:
    """Turn a raw smoke run into a status + normalized fields."""
    out, err = exec_result["stdout"], exec_result["stderr"]
    result = {k: v for k, v in exec_result.items() if k != "status_hint"}

    if exec_result["timed_out"]:
        result["status"] = "timeout"
        result["output_tail"] = tail(out + "\n" + err)
        return result

    payload = None
    if out.strip():
        try:
            payload = json.loads(out)
        except ValueError:
            payload = None

    if isinstance(payload, dict) and "ok" in payload:
        result["status"] = "accepts" if payload["ok"] else "rejects"
        result["error"] = str(payload.get("error", "")) or None
        result["output_tail"] = tail(out)
        return result

    blob = out + "\n" + err
    m = re.search(r"No module named '([^']+)'|cannot import name '([^']+)'", blob)
    if m:
        result["status"] = "missing_dependency"
        result["module"] = m.group(1) or m.group(2)
        result["output_tail"] = tail(blob)
        return result

    if payload is not None and kind == "json":
        # engine คืน JSON แต่ไม่ใช่ object ที่มี `ok` — ผิด contract
        result["status"] = "invalid_output"
        result["output_tail"] = tail(out)
        return result
    if kind == "json":
        # JSON engine ต้องคืน JSON เสมอ — ไม่มี JSON = crash (traceback)
        result["status"] = "crashed"
        result["output_tail"] = tail(blob)
        return result

    # custom command (smoke: ...) — วัดด้วย exit code
    result["status"] = "ok" if exec_result["exit_code"] == 0 else "crashed"
    result["output_tail"] = tail(blob)
    return result


def check_skill(path: Path, timeout: int, readme_text: str | None) -> dict:
    name = path.name
    findings = []
    meta = {}
    skill_md = path / "SKILL.md"

    if not skill_md.is_file():
        findings.append(finding("fail", "missing_skill_md",
                                "ไม่มี SKILL.md ในโฟลเดอร์สกิล"))
    else:
        meta = front_matter(skill_md)
        if not meta:
            findings.append(finding("fail", "no_frontmatter",
                                    "SKILL.md ไม่มี YAML frontmatter (---)"))
        else:
            if not meta.get("description", "").strip():
                findings.append(finding("fail", "missing_description",
                                        "frontmatter ไม่มี description"))
            if meta.get("name", "") and meta["name"] != name:
                findings.append(finding("warn", "name_mismatch",
                                        f"name '{meta['name']}' ไม่ตรงกับชื่อโฟลเดอร์ '{name}'"))
            desc = meta.get("description", "")
            if desc and "triggers on" not in desc.casefold():
                findings.append(finding("warn", "no_triggers",
                                        "description ไม่มี trigger keywords (Triggers on ...)"))

    scripts_dir = path / "scripts"
    spec = smoke_spec(scripts_dir, meta) if scripts_dir.is_dir() else {"kind": "none", "command": None}
    if not scripts_dir.is_dir():
        findings.append(finding("fail", "missing_scripts",
                                "ไม่มีโฟลเดอร์ scripts/ — สกิลไม่มี engine"))

    smoke = {"command": spec.get("command"), "status": "skipped",
             "exit_code": None, "timed_out": False, "duration_ms": 0,
             "module": None, "error": None, "output_tail": ""}

    if spec["kind"] == "none" and scripts_dir.is_dir():
        findings.append(finding("warn", "no_engine",
                                "ไม่มี scripts/run.py และไม่ได้ประกาศ `smoke:` ใน frontmatter — engine ไม่ถูกตรวจ"))
    elif spec["kind"] == "json" and (path / "scripts" / "run.py").resolve() == SELF_RUN:
        smoke["status"] = "skipped_self"  # กัน recursion: ห้าม smoke ตัวเอง
    elif spec["kind"] != "none":
        smoke.update(classify(execute(spec, timeout), spec["kind"]))
        if smoke["status"] in UNHEALTHY_STATUSES:
            label = {
                "missing_dependency": f"ขาด dependency: {smoke.get('module')}",
                "invalid_output": "engine คืน JSON แต่ไม่มี field `ok`",
                "crashed": "engine พัง (ไม่คืน JSON ตาม contract)",
                "timeout": f"engine ค้างเกิน {timeout} วินาที",
            }[smoke["status"]]
            findings.append(finding("fail", smoke["status"],
                                    f"smoke ของ {name} {label}"))

    if readme_text is not None and f"`{name}`" not in readme_text:
        findings.append(finding("fail", "not_in_readme",
                                f"ไม่มีบรรทัด `{name}` ใน README registry"))

    failed = any(f["severity"] == "fail" for f in findings)
    return {
        "name": name,
        "status": "fail" if failed else "pass",
        "engine": spec["kind"],
        "smoke": smoke,
        "findings": findings,
    }


def run(payload: dict) -> dict:
    if not isinstance(payload, dict):
        fail("input must be a JSON object")

    raw_dir = payload.get("dir")
    if raw_dir is None:
        root = Path("skills") if Path("skills").is_dir() \
            else SELF_RUN.parents[2]
    elif isinstance(raw_dir, str) and raw_dir.strip():
        root = Path(os.path.expanduser(raw_dir.strip()))
    else:
        fail("'dir' must be a non-empty string")
    if not root.is_dir():
        fail(f"'dir' does not exist: {root}")

    timeout = payload.get("timeout", DEFAULT_TIMEOUT)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) \
            or not 1 <= timeout <= MAX_TIMEOUT:
        fail(f"'timeout' must be 1..{MAX_TIMEOUT} seconds")

    only = payload.get("only")
    if only is not None:
        if not isinstance(only, list) or not only \
                or not all(isinstance(x, str) and x.strip() for x in only):
            fail("'only' must be a non-empty list of skill names")
        only = [x.strip() for x in only]

    try:
        skill_dirs = sorted(
            p for p in root.iterdir()
            if p.is_dir() and not p.name.startswith((".", "_"))
        )
    except OSError as e:
        fail(f"cannot read '{root}': {e}")
    if not skill_dirs:
        fail(f"'dir' contains no skills: {root}")

    names = [p.name for p in skill_dirs]
    if only:
        unknown = [n for n in only if n not in names]
        if unknown:
            fail(f"'only' contains unknown skills: {', '.join(unknown)} "
                 f"(found: {', '.join(names)})")
        skill_dirs = [p for p in skill_dirs if p.name in only]

    readme_path = root.parent / "README.md"
    readme_text = None
    if readme_path.is_file():
        try:
            readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            readme_text = None

    results = [check_skill(p, int(timeout), readme_text) for p in skill_dirs]

    failed = [r for r in results if r["status"] == "fail"]
    passed = [r for r in results if r["status"] == "pass"]
    statuses = [r["smoke"]["status"] for r in results]
    warnings = sum(1 for r in results for f in r["findings"]
                   if f["severity"] == "warn")

    next_actions = []
    for r in failed:
        for f in r["findings"]:
            if f["severity"] != "fail":
                continue
            if f["code"] == "missing_dependency":
                pkg = PIP_NAMES.get(r["smoke"].get("module") or "",
                                    r["smoke"].get("module"))
                next_actions.append(f"ติดตั้ง dependency ของ {r['name']}: pip install {pkg}")
            else:
                next_actions.append(f"แก้ {r['name']}: {f['message']} แล้วรัน skillcheck ซ้ำ")
    for r in results:
        for f in r["findings"]:
            if f["severity"] == "warn":
                next_actions.append(f"ควรแก้ {r['name']}: {f['message']}")
        if r["smoke"]["status"] == "skipped":
            next_actions.append(
                f"เพิ่ม 'smoke: <คำสั่ง smoke ที่รันได้>' ในหน้า SKILL.md ของ {r['name']} "
                f"เพื่อให้ skillcheck ตรวจ engine ได้")

    return {
        "ok": True,
        "skill": "skillcheck",
        "verdict": "pass" if not failed else "fail",
        "dir": str(root),
        "readme": str(readme_path) if readme_text is not None else None,
        "results": results,
        "totals": {
            "skills": len(results),
            "skills_passed": len(passed),
            "skills_failed": len(failed),
            "warnings": warnings,
            "engines_healthy": sum(1 for s in statuses if s in HEALTHY_STATUSES),
            "engines_unhealthy": sum(1 for s in statuses if s in UNHEALTHY_STATUSES),
            "engines_skipped": sum(1 for s in statuses
                                   if s in ("skipped", "skipped_self")),
        },
        "failures": [{"name": r["name"],
                      "findings": [f for f in r["findings"] if f["severity"] == "fail"]}
                     for r in failed],
        "next_actions": next_actions[:12],
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
