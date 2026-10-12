#!/usr/bin/env python3
"""Deterministic engine for skill: agent-loop.

Owns the phase state machine, its gates, and the run record. The model supplies
human judgement (task text, evidence notes, criteria, todos) and interprets the
JSON that comes back; it never decides the phase order itself.

    bootstrap_agent -> perceive -> goal_contract -> policy_check
    -> capability_discovery -> plan -> execute_loop

Usage:
    python scripts/run.py '{"op":"start","task":"...","criteria":["..."]}'
    python scripts/run.py '{"op":"advance","run":"<id>","note":"evidence"}'
    python scripts/run.py '{"op":"status","run":"<id>"}'
    python scripts/run.py '{"op":"capabilities"}'
    python scripts/run.py '{"op":"policy"}'
"""
import json
import os
import re
import sys
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

HOME = Path.home()


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(text: str, limit: int = 32) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return clean[:limit].strip("-") or "task"


def resolve_dir(value) -> Path:
    """Accept an OS-native path; also tolerate Git Bash /c/Users/... on Windows."""
    raw = str(value or ".").strip() or "."
    path = Path(raw)
    if not path.exists():
        match = re.match(r"^/([A-Za-z])/(.*)$", raw)
        if match:
            candidate = Path(match.group(1).upper() + ":/" + match.group(2))
            if candidate.exists():
                return candidate
    return path


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
    """Filesystem capability discovery - no network, no secrets."""
    root = root.resolve()
    found = {"skills": [], "agents": [], "commands": []}

    skill_dirs = [
        HOME / ".config/opencode/skills",
        HOME / ".agents/skills",
        HOME / ".claude/skills",
        root / ".opencode/skills",
        root / ".agents/skills",
        root / ".claude/skills",
    ]
    for directory in skill_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*/SKILL.md")) + sorted(directory.glob("*.md")):
            sid = path.parent.name if path.name == "SKILL.md" else path.stem
            meta = front_matter(path)
            found["skills"].append({
                "id": sid,
                "name": meta.get("name", sid),
                "description": meta.get("description", ""),
                "path": str(path),
            })

    for kind, dirs in (
        ("agents", [HOME / ".config/opencode/agent", root / ".opencode/agent"]),
        ("commands", [HOME / ".config/opencode/command", root / ".opencode/command"]),
    ):
        for directory in dirs:
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

    # Higher-precedence directories come first; keep the first id seen.
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
        files.append(str(path))
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                rules.append(stripped[2:].strip())
    return {"files": files, "rule_count": len(rules), "rules": rules[:40]}


def store(root: Path) -> Path:
    directory = root.resolve() / ".agent-loop"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_run(root: Path, run_id: str):
    path = store(root) / f"{run_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_run(root: Path, state: dict) -> Path:
    path = store(root) / f"{state['id']}.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def fail(message: str, **extra) -> dict:
    return {"ok": False, "error": message, **extra}


def need_list(payload: dict, key: str) -> list:
    value = payload.get(key) or []
    if isinstance(value, str):
        value = [value]
    return [str(item).strip() for item in value if str(item).strip()]


def op_start(payload: dict) -> dict:
    task = (payload.get("task") or "").strip()
    if not task:
        return fail("start requires a non-empty 'task'")
    root = resolve_dir(payload.get("dir"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    state = {
        "id": stamp + "-" + os.urandom(2).hex() + "-" + slug(task),
        "task": task,
        "created": utcnow(),
        "updated": utcnow(),
        "phase": "perceive",
        "completed": [],
        "criteria": need_list(payload, "criteria"),
        "todos": [],
        "policy": None,
        "capabilities": None,
        "history": [{
            "phase": "bootstrap_agent",
            "at": utcnow(),
            "note": "bootstrapped agent for task: " + task,
        }],
    }
    path = save_run(root, state)
    return {"ok": True, "run": state["id"], "phase": state["phase"], "path": str(path)}


def op_advance(payload: dict) -> dict:
    run_id = payload.get("run")
    if not run_id:
        return fail("advance requires 'run'")
    root = resolve_dir(payload.get("dir"))
    state = load_run(root, run_id)
    if state is None:
        return fail("unknown run: " + str(run_id))

    current = state["phase"]
    if current == "done" or current not in PHASES:
        return fail("run already finished", phase=current)

    note = (payload.get("note") or "").strip()
    state["criteria"] = list(dict.fromkeys(state.get("criteria") or [] + need_list(payload, "criteria")))
    state["todos"] = list(dict.fromkeys(state.get("todos") or [] + need_list(payload, "todos")))

    gate = GATES.get(current)
    missing = []
    if gate == "note" and len(note) < 10:
        missing.append("'note' with evidence (>= 10 chars)")
    if gate == "criteria" and not state["criteria"]:
        missing.append("at least one acceptance criterion ('criteria')")
    if gate == "policy":
        state["policy"] = load_policy(root)
        if state["policy"]["rule_count"] == 0:
            missing.append("at least one policy rule (no AGENTS.md bullets found)")
    if gate == "capabilities":
        state["capabilities"] = discover(root)
        if not state["capabilities"]["skills"]:
            missing.append("at least one discoverable skill")
    if gate == "todos" and not state["todos"]:
        missing.append("at least one todo ('todos')")
    if missing:
        return {"ok": False, "phase": current, "missing": missing}

    state["completed"] = list(dict.fromkeys((state.get("completed") or []) + [current]))
    state["history"].append({"phase": current, "at": utcnow(), "note": note})
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
            "capabilities": {
                kind: len(items) for kind, items in (state.get("capabilities") or {}).items()
            },
        }
    else:
        result["gate"] = GATES.get(state["phase"], "none")
    return result


def op_status(payload: dict) -> dict:
    run_id = payload.get("run")
    root = resolve_dir(payload.get("dir"))
    if not run_id:
        runs = sorted(path.stem for path in store(root).glob("*.json"))
        return {"ok": True, "runs": runs}
    state = load_run(root, run_id)
    if state is None:
        return fail("unknown run: " + str(run_id))
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
        "history": state["history"],
    }


def op_capabilities(payload: dict) -> dict:
    root = resolve_dir(payload.get("dir"))
    found = discover(root)
    return {"ok": True, "counts": {kind: len(items) for kind, items in found.items()}, **found}


def op_policy(payload: dict) -> dict:
    root = resolve_dir(payload.get("dir"))
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
    op = payload.get("op", "")
    if op not in OPS:
        print(json.dumps(fail("unknown op '" + str(op) + "'", ops=sorted(OPS)), ensure_ascii=False))
        sys.exit(2)
    result = OPS[op](payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
