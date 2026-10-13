#!/usr/bin/env python3
"""Deterministic engine for skill: knowledge.

สร้างและรักษาฐานความรู้ของโปรเจกต์ให้ถูกต้อง อัพเดทเสมอ — สกัดข้อเท็จจริงจาก
ไฟล์จริงทั้งหมด (ไม่ใช่ให้โมเดลเดา) แล้วบันทึกเป็น KNOWLEDGE.md ที่ประทับ
fingerprint เพื่อให้ verify ตรวจได้ว่าข้อมูลใหม่หรือเก่า

Usage:
  python scripts/run.py '{"op": "build"}'                    # ดึงข้อเท็จจริงเป็น JSON
  python scripts/run.py '{"op": "write"}'                    # เขียน/อัปเดต KNOWLEDGE.md
  python scripts/run.py '{"op": "verify"}'                   # ตรวจว่า KNOWLEDGE.md ยังใหม่?
  python scripts/run.py '{"op": "build", "dir": "../.."}'

Input schema:
  op    string  optional — build | write | verify (default build)
  dir   string  optional — โฟลเดอร์โปรเจกต์ (default ".")
  file  string  optional — ไฟล์ความรู้ สัมพัทธ์กับ dir (default "KNOWLEDGE.md")

สิ่งที่สกัด: ชนิดโปรเจกต์/ชื่อ, ภาษาตาม extension, manifest (package.json scripts +
dependencies, requirements/pyproject, lockfile), target ใน Makefile, สกิลทั้งหมด
(ชื่อ + description), สถานะ git (branch/commit/จำนวนไฟล์ที่ค้าง), ชื่อ key ใน
.env.example (อ่านเฉพาะชื่อ ไม่แตะค่า และไม่แตะ .env จริง), entry point ที่เจอ

Exit codes: 0 = engine รันครบ (อ่าน `verdict`) / 1 = input ไม่ครบ / 2 = JSON ผิดรูปแบบ
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", "vendor",
             "venv", ".venv", ".next", ".cache", ".idea", ".vscode"}
MAX_FILES = 5000
MAX_LIST = 100
DEFAULT_FILE = "KNOWLEDGE.md"

ENV_EXAMPLES = (".env.example", ".env.sample", ".env.dist")
ENTRY_CANDIDATES = ("main.py", "app.py", "index.js", "index.ts", "main.ts",
                    "main.go", "src/index.js", "src/index.ts")
LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".go": "go", ".rs": "rust",
    ".java": "java", ".rb": "ruby", ".php": "php", ".sh": "shell",
    ".md": "markdown", ".json": "json", ".yml": "yaml", ".yaml": "yaml",
    ".toml": "toml", ".css": "css", ".html": "html", ".sql": "sql",
}
KIND_MARKERS = [
    ("node", ("package.json",)), ("python", ("pyproject.toml", "setup.py",
                                              "requirements.txt")),
    ("rust", ("Cargo.toml",)), ("go", ("go.mod",)),
]


def fail(message: str) -> None:
    print(json.dumps({"ok": False, "skill": "knowledge", "error": message},
                     ensure_ascii=False, indent=2))
    sys.exit(1)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_git(root: Path, *args) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, timeout=10,
                              errors="replace")
        return proc.stdout.strip() if proc.returncode == 0 else None
    except OSError:
        return None


def walk_files(root: Path, exclude: Path | None = None):
    count = 0
    for p in sorted(root.rglob("*")):
        if count >= MAX_FILES:
            break
        if not p.is_file():
            continue
        if exclude is not None and p.resolve() == exclude:
            continue                        # ไฟล์ความรู้ไม่นับรวมใน facts ของตัวเอง
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".")
               for part in rel.parts[:-1]):
            continue
        count += 1
        yield p


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


def read_json(path: Path):
    try:
        if path.stat().st_size > 1_000_000:
            return None
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None


def extract_manifests(root: Path, files: set) -> dict:
    out = {"node": None, "python": [], "lockfiles": []}
    pkg = root / "package.json"
    if "package.json" in files:
        data = read_json(pkg)
        if isinstance(data, dict):
            out["node"] = {
                "name": data.get("name"),
                "version": data.get("version"),
                "main": data.get("main"),
                "scripts": dict(sorted(
                    (data.get("scripts") or {}).items())[:MAX_LIST]),
                "dependencies": len(data.get("dependencies") or {}),
                "dev_dependencies": len(data.get("devDependencies") or {}),
            }
    req = root / "requirements.txt"
    if req.is_file():
        try:
            lines = [ln.strip() for ln in
                     req.read_text(encoding="utf-8", errors="replace")
                     .splitlines()]
            out["python"].append({
                "file": "requirements.txt",
                "packages": [ln for ln in lines
                             if ln and not ln.startswith("#")][:MAX_LIST],
            })
        except OSError:
            pass
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        name = re.search(r"^name\s*=\s*\"?([\w.\-]+)\"?", text, re.M)
        deps = re.findall(r"\"([A-Za-z0-9_\-.]+[<>=~!][^\"]*)\"", text)
        out["python"].append({"file": "pyproject.toml",
                              "name": name.group(1) if name else None,
                              "declared_pins": sorted(set(deps))[:MAX_LIST]})
    for lock in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                 "poetry.lock", "uv.lock", "Cargo.lock", "go.sum"):
        if lock in files:
            out["lockfiles"].append(lock)
    return out


def extract_makefile(root: Path) -> list:
    path = root / "Makefile"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    targets = []
    for m in re.finditer(r"^([A-Za-z0-9_.\-]+):(?!=)", text, re.M):
        name = m.group(1)
        if name not in (".PHONY", ".DEFAULT", ".SILENT") and name not in targets:
            targets.append(name)
    return targets[:MAX_LIST]


def extract_skills(root: Path) -> list:
    out, seen = [], set()
    for pattern in ("*/SKILL.md", "skills/*/SKILL.md"):
        for skill_md in sorted(root.glob(pattern)):
            if skill_md.parent.name in seen:
                continue
            seen.add(skill_md.parent.name)
            meta = front_matter(skill_md)
            scripts = skill_md.parent / "scripts"
            out.append({
                "name": skill_md.parent.name,
                "description": meta.get("description", "")[:160],
                "engine": ("json" if (scripts / "run.py").is_file()
                           else "custom" if meta.get("smoke") else "none"),
            })
    return out[:MAX_LIST]


def extract_env_keys(root: Path) -> dict:
    """อ่านเฉพาะชื่อ key จากไฟล์ตัวอย่าง — ไม่แตะ .env จริง ไม่อ่านค่า"""
    out = {}
    for name in ENV_EXAMPLES:
        path = root / name
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8",
                                   errors="replace").splitlines()
        except OSError:
            continue
        keys = [m.group(1) for ln in lines
                if (m := re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln))]
        out[name] = sorted(set(keys))[:MAX_LIST]
    return out


def extract_git(root: Path, exclude: Path | None = None) -> dict | None:
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        return None
    last = run_git(root, "log", "-1", "--format=%h|%cI|%s")
    dirty = run_git(root, "status", "--porcelain")
    dirty_count = None
    if dirty is not None:
        rel_target = (str(exclude.relative_to(root)).replace("\\", "/")
                      if exclude and root in exclude.parents else None)
        lines = [ln for ln in dirty.splitlines()
                 if ln[3:].strip().strip('"') != rel_target]
        dirty_count = len(lines)
    return {
        "branch": branch,
        "last_commit": (last.split("|", 2) if last else None),
        "dirty_files": dirty_count,
    }


def build_facts(root: Path, exclude: Path | None = None) -> dict:
    langs, files_seen = {}, set()
    for p in walk_files(root, exclude):
        rel = str(p.relative_to(root)).replace("\\", "/")
        files_seen.add(rel)
        lang = LANG_BY_EXT.get(p.suffix.casefold())
        if lang:
            langs[lang] = langs.get(lang, 0) + 1

    kinds = [k for k, markers in KIND_MARKERS
             if any((root / m).exists() for m in markers)]
    name = None
    node = None
    manifests = extract_manifests(root, files_seen)
    if manifests["node"]:
        node = manifests["node"]
        name = node.get("name")
    if name is None and manifests["python"]:
        name = next((m.get("name") for m in manifests["python"]
                     if m.get("name")), None)

    entry = [c for c in ENTRY_CANDIDATES if (root / c).is_file()]
    if node and node.get("main") and (root / str(node["main"])).is_file():
        entry.insert(0, str(node["main"]))

    return {
        "project": {
            "root": str(root),
            "name": name or root.resolve().name,
            "kind": kinds[0] if len(kinds) == 1
                    else "mixed" if len(kinds) > 1 else "other",
        },
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        "file_count": len(files_seen),
        "manifests": manifests,
        "makefile_targets": extract_makefile(root),
        "skills": extract_skills(root),
        "git": extract_git(root, exclude),
        "env_example_keys": extract_env_keys(root),
        "entry_candidates": entry[:MAX_LIST],
    }


def fingerprint(facts: dict) -> str:
    canonical = json.dumps(facts, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]


def esc(value) -> str:
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= 200 else text[:197] + "..."


def render(facts: dict, fp: str, generated_at: str) -> str:
    p = facts["project"]
    lines = [f"# Knowledge — {esc(p['name'])}", ""]
    lines += [
        f"> generated by the knowledge skill · {generated_at} · fingerprint `{fp}`",
        "> รันซ้ำด้วย op write เพื่ออัปเดต · ตรวจความใหม่ด้วย op verify", "",
        "## Project", "",
        f"- kind: {p['kind']} · root: `{esc(p['root'])}`",
        f"- files: {facts['file_count']}", "",
        "## Languages", ""]
    lines += [f"- {lang}: {count}" for lang, count in
              facts["languages"].items()] or ["- (ไม่พบไฟล์ที่จับคู่ภาษาได้)"]
    lines += ["", "## Commands", ""]
    node = facts["manifests"]["node"]
    if node and node.get("scripts"):
        lines += [f"- npm script `{k}`: {esc(v)}"
                  for k, v in node["scripts"].items()]
    if facts["makefile_targets"]:
        lines += [f"- make target: {', '.join(f'`{t}`' for t in facts['makefile_targets'])}"]
    if not ((node and node.get("scripts")) or facts["makefile_targets"]):
        lines.append("- (ไม่มี script ใน manifest หรือ Makefile)")
    lines += ["", "## Dependencies", ""]
    if node:
        lines.append(f"- node: runtime {node['dependencies']} ตัว, dev {node['dev_dependencies']} ตัว"
                     + (f" · lockfile: {', '.join(facts['manifests']['lockfiles'])}"
                        if facts['manifests']['lockfiles'] else ""))
    for m in facts["manifests"]["python"]:
        pkgs = m.get("packages") or m.get("declared_pins") or []
        lines.append(f"- {m['file']}: {', '.join(esc(x) for x in pkgs) or '(ว่าง)'}")
    if not node and not facts["manifests"]["python"]:
        lines.append("- (ไม่มี manifest dependencies)")
    if facts["skills"]:
        lines += ["", "## Skills", ""]
        lines += [f"- `{s['name']}` ({s['engine']}): {esc(s['description'])}"
                  for s in facts["skills"]]
    if facts["git"]:
        g = facts["git"]
        commit = " · ".join(g["last_commit"]) if g["last_commit"] else "-"
        lines += ["", "## Git", "",
                  f"- branch: {g['branch']} · dirty files: {g['dirty_files']}",
                  f"- last commit: {esc(commit)}"]
    if facts["env_example_keys"]:
        lines += ["", "## Env keys (จากไฟล์ตัวอย่าง — ดูค่าจริงเองใน .env ของคุณ)", ""]
        for name, keys in facts["env_example_keys"].items():
            lines.append(f"- {name}: {', '.join('`' + k + '`' for k in keys)}")
    if facts["entry_candidates"]:
        lines += ["", "## Entry points", ""]
        lines += [f"- `{c}`" for c in facts["entry_candidates"]]
    lines.append("")
    return "\n".join(lines)


def changed_since(root: Path, iso_time: str, knowledge: Path) -> list:
    """ไฟล์ที่เปลี่ยนหลัง generated_at — git ถ้ามี ไม่งั้นใช้ mtime"""
    dirty = run_git(root, "status", "--porcelain")
    if dirty is not None:
        rel_target = (str(knowledge.relative_to(root)).replace("\\", "/")
                      if root in knowledge.parents else None)
        return [ln[3:].strip() for ln in dirty.splitlines()
                if ln[3:].strip().strip('"') != rel_target][:20]
    try:
        cutoff = knowledge.stat().st_mtime
    except OSError:
        try:
            cutoff = datetime.fromisoformat(
                iso_time.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return []
    changed = []
    for p in walk_files(root):
        if p == knowledge:
            continue
        try:
            if p.stat().st_mtime > cutoff:
                changed.append(str(p.relative_to(root)).replace("\\", "/"))
        except OSError:
            continue
        if len(changed) >= 20:
            break
    return changed


def resolve_target(root: Path, raw_file: str) -> Path:
    target = (root / raw_file).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        fail(f"'file' must stay inside 'dir': {raw_file}")
    return target


def run(payload: dict) -> dict:
    if not isinstance(payload, dict):
        fail("input must be a JSON object")
    op = payload.get("op", "build")
    if op not in ("build", "write", "verify"):
        fail("'op' must be one of: build, write, verify")
    raw_dir = payload.get("dir", ".")
    if not isinstance(raw_dir, str) or not raw_dir.strip():
        fail("'dir' must be a non-empty string")
    root = Path(raw_dir.strip())
    if not root.is_dir():
        fail(f"'dir' does not exist: {root}")
    root = root.resolve()
    raw_file = payload.get("file", DEFAULT_FILE)
    if not isinstance(raw_file, str) or not raw_file.strip() \
            or raw_file.startswith("~"):
        fail("'file' must be a non-empty relative path")
    target = resolve_target(root, raw_file)

    facts = build_facts(root, exclude=target)
    fp = fingerprint(facts)
    generated_at = utcnow()

    if op in ("build", "write"):
        verdict = "pass"
        report = {"facts": facts, "fingerprint": fp}
        if op == "write":
            if target.exists():
                existing = target.read_text(encoding="utf-8",
                                            errors="replace")[:500]
                if "generated by the knowledge skill" not in existing:
                    fail(f"file exists and was not generated by this skill: "
                         f"{raw_file} — choose another 'file' or delete it")
            target.write_text(render(facts, fp, generated_at),
                              encoding="utf-8")
            report["file"] = str(target)
        return {"ok": True, "skill": "knowledge", "op": op,
                "verdict": verdict, **report,
                "next_actions": ([] if op == "build" else
                                 [f"อัปเดตแล้ว: {raw_file} — "
                                  "รัน op verify เมื่อสงสัยว่าข้อมูลเก่า"])}

    # op == verify
    if not target.is_file():
        return {"ok": True, "skill": "knowledge", "op": op,
                "verdict": "fail", "facts": facts, "fingerprint": fp,
                "reason": f"ไม่มีไฟล์ความรู้: {raw_file}",
                "next_actions": [f"รัน op write เพื่อสร้าง {raw_file}"]}
    text = target.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"fingerprint `([0-9a-f]{12})`", text)
    m2 = re.search(r"generated by the knowledge skill · (\S+)", text)
    if not m:
        return {"ok": True, "skill": "knowledge", "op": op,
                "verdict": "fail", "facts": facts, "fingerprint": fp,
                "reason": "ไฟล์ไม่มี fingerprint ของ knowledge skill",
                "next_actions": [f"รัน op write เพื่อสร้าง {raw_file} ใหม่"]}
    fresh = m.group(1) == fp
    changed = [] if fresh else changed_since(
        root, m2.group(1) if m2 else generated_at, target)
    return {
        "ok": True, "skill": "knowledge", "op": op,
        "verdict": "pass" if fresh else "fail",
        "facts": facts, "fingerprint": fp,
        "file_fingerprint": m.group(1),
        "generated_at": m2.group(1) if m2 else None,
        "changed_since": changed,
        "next_actions": ([] if fresh else
                         [f"{raw_file} เก่าแล้ว (fingerprint ไม่ตรง) — "
                          "รัน op write เพื่ออัปเดต"]
                         + ([f"ไฟล์ที่เปลี่ยนหลังสร้าง: "
                             f"{', '.join(changed[:5])}"] if changed else [])),
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
