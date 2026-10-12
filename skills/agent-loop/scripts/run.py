#!/usr/bin/env python3
"""Deterministic engine for skill: agent-loop.

Owns the phase state machine, its gates, and the run record. The model supplies
human judgement (task text, evidence notes, criteria, todos) and interprets the
JSON that comes back; it never decides the phase order itself.

    bootstrap_agent -> perceive -> goal_contract -> policy_check
    -> capability_discovery -> plan -> execute_loop

Usage:
    python scripts/run.py '{"op":"start","task":"..."}'
    python scripts/run.py '{"op":"advance","run":"<id>","note":"evidence"}'
    python scripts/run.py '{"op":"status","run":"<id>"}'
    python scripts/run.py '{"op":"capabilities"}'
    python scripts/run.py '{"op":"policy"}'

Exit codes: 0 = ok, 1 = blocked or engine error, 2 = malformed input.
Every response is a single JSON object on stdout.
"""
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PHASES = [
    "bootstrap_agent",
    "perceive",
    "goal_contract",
    "policy_check",
    "capability_discovery",
    "plan",
    "execute_loop",
]

# What must exist to *complete* each phase. bootstrap_agent is completed by start.
GATES = {
    "perceive": "note",
    "goal_contract": "criteria",
    "policy_check": "policy",
    "capability_discovery": "capabilities",
    "plan": "todos",
    "execute_loop": "note",
}

KINDS = ("skills", "agents", "commands")
HOME = Path.home()
LOCK_TIMEOUT = 5.0
RUN_ID = re.compile(r"[A-Za-z0-9._-]{1,120}\Z")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def need_list(payload: dict, key: str) -> list:
    value = payload.get(key)
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    texts = [as_text(item) for item in items]
    return [text for text in texts if text]


def dedupe(items: list) -> list:
    return list(dict.fromkeys(items))


def slug(text: str, limit: int = 32) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return clean[:limit].strip("-") or "task"


def resolve_dir(value) -> Path:
    """Accept an OS-native path; also tolerate a Git Bash /c/Users/... path."""
    raw = as_text(value) or "."
    match = re.match(r"^/([A-Za-z])/(.*)$", raw)
    if match:
        raw = match.group(1).upper() + ":/" + match.group(2)
    return Path(raw)


def workdir(payload: dict):
    root = resolve_dir(payload.get("dir"))
    if not root.is_dir():
        return None, fail("'dir' is not an existing directory: " + str(root))
    return root.resolve(), None


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


def discover(root: Path) -> dict:
    """Filesystem capability discovery - no network, no credentials."""
    root = root.resolve()
    found = {kind: [] for kind in KINDS}

    # Project sources first: first id seen wins, matching OpenCode precedence.
    skill_dirs = [
        root / ".opencode/skills",
        root / ".agents/skills",
        root / ".claude/skills",
        HOME / ".config/opencode/skills",
        HOME / ".agents/skills",
        HOME / ".claude/skills",
    ]
    for directory in skill_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*/SKILL.md")) + sorted(directory.glob("*.md")):
            meta = front_matter(path)
            if path.name != "SKILL.md" and not meta:
                continue  # a flat *.md counts as a skill only with frontmatter
            sid = path.parent.name if path.name == "SKILL.md" else path.stem
            found["skills"].append({
                "id": sid,
                "name": meta.get("name", sid),
                "description": meta.get("description", ""),
                "path": str(path),
            })

    for kind, name in (("agents", "agent"), ("commands", "command")):
        for directory in (root / ".opencode" / name, HOME / ".config/opencode" / name):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.md")):
                meta = front_matter(path)
                found[kind].append({
                    "id": path.stem,
                    "name": meta.get("name", path.stem),
                    "description": meta.get("description", ""),
                    "path": str(path),
                })

    for items in found.values():
        seen, unique = set(), []
        for item in items:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            unique.append(item)
        items[:] = unique
    return found


def load_policy(root: Path) -> dict:
    root = root.resolve()
    candidates = [HOME / ".config/opencode/AGENTS.md"]
    current = root
    while True:
        candidates.append(current / "AGENTS.md")
        if current.parent == current:
            break
        current = current.parent

    files, rules = [], []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files.append(str(path))
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                rules.append(stripped[2:].strip())
    return {"files": files, "rule_count": len(rules), "rules": rules[:40]}


def store_path(root: Path) -> Path:
    """Where run records live. Never creates anything."""
    return root.resolve() / ".agent-loop"


def ensure_store(root: Path) -> Path:
    directory = store_path(root)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@contextmanager
def run_lock(directory: Path):
    """Serialize the read-modify-write of a run record."""
    lock_path = directory / ".lock"
    deadline = time.monotonic() + LOCK_TIMEOUT
    while True:
        try:
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(handle)
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise TimeoutError("another run.py is mid-write; retry shortly")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            os.unlink(str(lock_path))
        except OSError:
            pass


def valid_run_id(run_id: str) -> bool:
    return bool(RUN_ID.fullmatch(run_id)) and ".." not in run_id


def load_run(root: Path, run_id: str):
    base = store_path(root)
    path = base / (run_id + ".json")
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict) or state.get("phase") not in PHASES + ["done"]:
        return None
    return state


def save_run(root: Path, state: dict) -> Path:
    directory = ensure_store(root)
    path = directory / (state["id"] + ".json")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))
    return path


def fail(message: str, **extra) -> dict:
    return {"ok": False, "error": message, **extra}


def op_start(payload: dict) -> dict:
    task = as_text(payload.get("task"))
    if not task:
        return fail("start requires a non-empty 'task'")
    root, error = workdir(payload)
    if error:
        return error
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    state = {
        "id": stamp + "-" + os.urandom(2).hex() + "-" + slug(task),
        "task": task,
        "created": utcnow(),
        "updated": utcnow(),
        "phase": "perceive",
        "completed": [],
        "criteria": [],
        "todos": [],
        "policy": None,
        "capabilities": None,
        "blocked": 0,
        "history": [{
            "phase": "bootstrap_agent",
            "at": utcnow(),
            "note": "bootstrapped agent for task: " + task,
        }],
    }
    path = save_run(root, state)
    return {"ok": True, "run": state["id"], "phase": state["phase"], "path": str(path)}


def op_advance(payload: dict) -> dict:
    run_id = as_text(payload.get("run"))
    if not run_id:
        return fail("advance requires 'run'")
    if not valid_run_id(run_id):
        return fail("invalid run id: " + run_id)
    root, error = workdir(payload)
    if error:
        return error

    try:
        with run_lock(ensure_store(root)):
            return advance_locked(root, run_id, payload)
    except TimeoutError as timeout:
        return fail(str(timeout), phase="unknown")
    except OSError as os_error:
        return fail("cannot write run record: " + str(os_error))


def advance_locked(root: Path, run_id: str, payload: dict) -> dict:
    state = load_run(root, run_id)
    if state is None:
        return fail("unknown run: " + run_id)

    current = state["phase"]
    if current == "done" or current not in PHASES:
        return fail("run already finished", phase=current)

    note = as_text(payload.get("note"))
    criteria = need_list(payload, "criteria")
    todos = need_list(payload, "todos")

    # Criteria and todos belong to exactly one phase each; no pre-filling.
    if criteria:
        if current != "goal_contract":
            return fail("'criteria' is only accepted while completing goal_contract", phase=current)
        state["criteria"] = dedupe((state.get("criteria") or []) + criteria)
    if todos:
        if current != "plan":
            return fail("'todos' is only accepted while completing plan", phase=current)
        state["todos"] = dedupe((state.get("todos") or []) + todos)

    gate = GATES.get(current)
    missing = []
    engine_note = None
    if gate == "note" and len(note) < 10:
        missing.append("'note' with evidence (>= 10 chars)")
    if gate == "criteria" and not state["criteria"]:
        missing.append("at least one acceptance criterion ('criteria')")
    if gate == "policy":
        state["policy"] = load_policy(root)
        if state["policy"]["rule_count"] == 0:
            missing.append("at least one policy rule (no AGENTS.md bullets found)")
        else:
            engine_note = "loaded %d policy rules from %d file(s)" % (
                state["policy"]["rule_count"], len(state["policy"]["files"]))
    if gate == "capabilities":
        caps = discover(root)
        state["capabilities"] = caps
        ids = {item["id"].lower() for kind in KINDS for item in caps[kind]}
        if not ids:
            missing.append("no discoverable skills/agents/commands")
        elif not any(sid in note.lower() for sid in ids):
            missing.append(
                "'note' must name at least one discovered capability id (e.g. "
                + ", ".join(sorted(ids)[:5]) + ")")
        else:
            engine_note = "discovered " + ", ".join(
                "%s=%d" % (kind, len(caps[kind])) for kind in KINDS)
    if gate == "todos" and not state["todos"]:
        missing.append("at least one todo ('todos')")

    if missing:
        state["blocked"] = int(state.get("blocked") or 0) + 1
        state["updated"] = utcnow()
        state["history"].append({
            "phase": current,
            "at": state["updated"],
            "blocked": True,
            "missing": missing,
        })
        save_run(root, state)
        return {"ok": False, "phase": current, "missing": missing,
                "blocked_attempts": state["blocked"]}

    state["completed"] = dedupe((state.get("completed") or []) + [current])
    state["history"].append({
        "phase": current,
        "at": utcnow(),
        "note": engine_note or note,
    })
    index = PHASES.index(current)
    if index + 1 < len(PHASES):
        state["phase"] = PHASES[index + 1]
    else:
        state["phase"] = "done"
        state["finished"] = utcnow()
    state["updated"] = utcnow()
    save_run(root, state)

    result = {"ok": True, "completed": current, "phase": state["phase"]}
    if state["phase"] == "done":
        result["summary"] = {
            "task": state["task"],
            "criteria": state["criteria"],
            "todos": state["todos"],
            "policy_rules": (state.get("policy") or {}).get("rule_count"),
            "capabilities": {kind: len((state.get("capabilities") or {}).get(kind, []))
                             for kind in KINDS},
            "blocked_attempts": state["blocked"],
        }
    else:
        result["gate"] = GATES.get(state["phase"], "none")
    return result


def op_status(payload: dict) -> dict:
    root, error = workdir(payload)
    if error:
        return error
    run_id = as_text(payload.get("run"))
    directory = store_path(root)
    if not run_id:
        runs = sorted(path.stem for path in directory.glob("*.json")) if directory.is_dir() else []
        return {"ok": True, "runs": runs}
    if not valid_run_id(run_id):
        return fail("invalid run id: " + run_id)
    state = load_run(root, run_id)
    if state is None:
        return fail("unknown run: " + run_id)
    phase = state["phase"]
    return {
        "ok": True,
        "run": run_id,
        "task": state["task"],
        "phase": phase,
        "completed": state["completed"],
        "gate": GATES.get(phase, "none"),
        "criteria": state["criteria"],
        "todos": state["todos"],
        "blocked_attempts": state.get("blocked", 0),
        "history": state["history"],
    }


def op_capabilities(payload: dict) -> dict:
    root, error = workdir(payload)
    if error:
        return error
    found = discover(root)
    return {"ok": True, "counts": {kind: len(found[kind]) for kind in KINDS}, **found}


def op_policy(payload: dict) -> dict:
    root, error = workdir(payload)
    if error:
        return error
    return {"ok": True, **load_policy(root)}


OPS = {
    "start": op_start,
    "advance": op_advance,
    "status": op_status,
    "capabilities": op_capabilities,
    "policy": op_policy,
}


def main() -> None:
    raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        print(json.dumps(fail("invalid JSON input: " + str(error)), ensure_ascii=False))
        sys.exit(2)
    if not isinstance(payload, dict):
        print(json.dumps(fail("input must be a JSON object"), ensure_ascii=False))
        sys.exit(2)
    op = as_text(payload.get("op"))
    if op not in OPS:
        print(json.dumps(fail("unknown op '" + op + "'", ops=sorted(OPS)), ensure_ascii=False))
        sys.exit(2)
    try:
        result = OPS[op](payload)
    except Exception as error:  # never leak a traceback: the JSON contract holds
        print(json.dumps(
            fail("engine error: " + type(error).__name__ + ": " + str(error)),
            ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
