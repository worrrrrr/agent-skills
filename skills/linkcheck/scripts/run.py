#!/usr/bin/env python3
"""Deterministic engine for skill: linkcheck.

ตรวจลิงก์และไฟล์อ้างอิงที่พังในเอกสารแบบรันเองได้ — สแกนไฟล์ Markdown ใต้ `dir`
(ข้าม .git/node_modules/โฟลเดอร์ซ่อน) แล้วตรวจ 3 อย่าง:

  1. markdown link/image `[text](target)` และ reference definition `[ref]: target`
     — relative target ต้องชี้ถึงไฟล์/โฟลเดอร์จริง; ถ้า target เป็น .md + anchor
     ต้องมี heading จริง (GitHub slug) หรือ id/name ในไฟล์นั้น
  2. anchor ภายในไฟล์เดียวกัน `[text](#anchor)`
  3. path ใน inline code span (นอก fence) ที่ลงท้ายด้วย extension ที่รู้จัก
     เช่น `scripts/run.py` — ต้อง resolve ได้จากโฟลเดอร์ไฟล์นั้นหรือจาก root

links/anchors = สัญญาณชัดเจน → ผิด = fail; code-span path = heuristic → ผิด = warn
(เอกสารมักอ้าง path เป็นแนวคิด เช่น `AGENTS.md` ที่ไม่ได้อยู่ใน repo)

Usage:
  python scripts/run.py '{}'                     # สแกน cwd ทั้งหมด
  python scripts/run.py '{"dir": "../.."}'
  python scripts/run.py '{"check_http": true}'   # ตรวจ http link ภายนอกด้วย

Input schema:
  dir        string  optional — โฟลเดอร์ตั้งต้นของเอกสาร (default: ".")
  check_http bool    optional — ตรวจ http(s) link จริง (default false)
  timeout    number  optional — timeout ต่อ http link วินาที (default 10, max 60)

Exit codes: 0 = engine รันครบ (อ่าน `verdict`) / 1 = input ไม่ครบ / 2 = JSON ผิดรูปแบบ
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".agent-loop", ".next",
             "dist", "build", "vendor", "venv", ".venv"}
FILE_EXTS = {".py", ".md", ".ts", ".js", ".jsx", ".tsx", ".json", ".txt",
             ".se1", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".html",
             ".css", ".sh", ".csv"}
USER_AGENT = "linkcheck-skill/1.0"
MAX_REPORT = 50

FENCE = re.compile(r"^\s{0,3}(```|~~~)")
INLINE_LINK = re.compile(
    r"!?\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]*)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
HTML_ANCHOR = re.compile(
    r"<(?:a|span|div)[^>]*(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)([^`]+?)(?<!`)\1(?!`)")
SPAN_PATH = re.compile(r"\A\.?[\w.\-]+(?:/[\w.\-]+)*\Z")
LINE_ANCHOR = re.compile(r"\AL\d+(-L?\d+)?\Z", re.IGNORECASE)


def fail(message: str) -> None:
    print(json.dumps({"ok": False, "skill": "linkcheck", "error": message},
                     ensure_ascii=False, indent=2))
    sys.exit(1)


def slugify(text: str) -> str:
    """GitHub-style anchor slug; keeps Thai/word chars, - and _."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # [text](url) -> text
    t = t.replace("`", "").replace("*", "")
    t = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE)
    t = re.sub(r"\s+", "-", t.strip().casefold())
    return t


def md_files(root: Path):
    for p in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIRS or part.startswith(".")
               for part in p.relative_to(root).parts[:-1]):
            continue
        yield p


def anchors_of(text: str) -> set:
    anchors = set()
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m and m.group(1).strip():
            anchors.add(slugify(m.group(1)))
        anchors.update(HTML_ANCHOR.findall(line))
    return anchors


def check_target(target: str, file_dir: Path, root: Path, text_cache: dict):
    """Classify one link target. Returns (status, detail)."""
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if not target:
        return "empty", "ไม่มี target"
    low = target.casefold()
    if low.startswith(("http://", "https://")):
        return "external", None
    if low.startswith(("mailto:", "tel:", "data:")):
        return "skip", None

    path_part, _, anchor = target.partition("#")
    path_part = urllib.parse.unquote(path_part).replace("\\", "/")
    if not path_part:
        resolved = file_dir                     # anchor ภายในไฟล์เดียวกัน
    else:
        p = Path(path_part)
        if p.is_absolute() or path_part.startswith("~"):
            return "skip", None
        resolved = None
        for cand in (file_dir / path_part, root / path_part):
            if cand.exists():
                resolved = cand
                break
        if resolved is None:
            return "broken_target", f"ไม่พบไฟล์: {path_part}"

    if not anchor:
        return "ok", None
    if LINE_ANCHOR.match(anchor):
        return "ok", None                       # เช่น file.py#L10
    if resolved.is_dir() or resolved.suffix.casefold() != ".md":
        return "ok", None                       # anchor นอก .md ตรวจไม่ได้ — ข้าม
    if resolved not in text_cache:
        text_cache[resolved] = resolved.read_text(
            encoding="utf-8", errors="replace")
    if anchor.casefold() in anchors_of(text_cache[resolved]):
        return "ok", None
    return "broken_anchor", f"ไม่มี anchor '#{anchor}' ใน {resolved.name}"


def check_http(target: str, timeout: int):
    req = urllib.request.Request(target, method="HEAD",
                                 headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return "external_ok", resp.status
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 501):           # HEAD ถูกบล็อก — ลอง GET
            try:
                req = urllib.request.Request(
                    target, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return "external_ok", resp.status
            except urllib.error.HTTPError as e2:
                return "external_broken", e2.code
            except (urllib.error.URLError, OSError, TimeoutError) as e2:
                return "external_error", str(e2.reason)
        return "external_broken", e.code
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return "external_error", str(getattr(e, "reason", e))


def span_bases(file_dir: Path, root: Path) -> list:
    """Where a prose path may reasonably point: the file's own dir, its skill
    root (nearest ancestor with SKILL.md), the scan root, and each skill folder."""
    def add_skill(folder: Path) -> None:
        bases.append(folder)
        if (folder / "scripts").is_dir():
            bases.append(folder / "scripts")

    bases = [file_dir]
    for parent in file_dir.parents:
        if parent == root.parent:
            break
        if (parent / "SKILL.md").is_file():
            add_skill(parent)
            break
    bases.append(root)
    for holder in (root, root / "skills"):
        if holder.is_dir():
            for folder in holder.iterdir():
                if folder.is_dir() and (folder / "SKILL.md").is_file():
                    add_skill(folder)
    return list(dict.fromkeys(bases))[:20]


def check_span(span: str, file_dir: Path, root: Path):
    """Inline code span ที่หน้าตาเหมือน path จริงหรือไม่ — heuristic, warn เท่านั้น."""
    if " " in span or any(ch in span for ch in ":*()<>[]{}$'\"\\"):
        return None
    if span.startswith(("~", "/", "http")):
        return None
    norm = span.replace("\\", "/")
    if not SPAN_PATH.match(norm):
        return None
    if Path(norm).suffix.casefold() not in FILE_EXTS:
        return None
    for base in span_bases(file_dir, root):
        if (base / norm).exists():
            return "ok"
    return "broken_ref"


def scan_file(path: Path, root: Path, check_http_links: bool,
              timeout: int, text_cache: dict) -> dict:
    text = text_cache.setdefault(
        path, path.read_text(encoding="utf-8", errors="replace"))
    file_dir = path.parent
    findings = []
    links = refs_checked = external = 0
    in_fence = False

    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # ดึง link จากบรรทัดที่ถูกตัด inline code span ออกแล้ว — `[text](target)`
        # ที่เขียนใน backtick เป็นเอกสาร ไม่ใช่ลิงก์จริง
        prose = CODE_SPAN.sub(" ", line)
        targets = [m for m in INLINE_LINK.findall(prose)]
        m = REF_DEF.match(prose)
        if m:
            targets.append(m.group(1))
        for raw in targets:
            links += 1
            status, detail = check_target(raw, file_dir, root, text_cache)
            if status == "external":
                external += 1
                if check_http_links:
                    status, detail = check_http(raw, timeout)
                    if status != "external_ok":
                        findings.append({"severity": "fail", "code": status,
                                         "target": raw, "message": detail})
            elif status == "broken_target":
                findings.append({"severity": "fail", "code": status,
                                 "target": raw, "message": detail})
            elif status == "broken_anchor":
                findings.append({"severity": "fail", "code": status,
                                 "target": raw, "message": detail})
            elif status == "empty":
                findings.append({"severity": "warn", "code": "empty_link",
                                 "target": raw, "message": "ลิงก์ไม่มี target"})

        for span in CODE_SPAN.findall(line):
            verdict_span = check_span(span[1], file_dir, root)
            if verdict_span is None:
                continue
            refs_checked += 1
            if verdict_span == "broken_ref":
                findings.append({"severity": "warn", "code": "broken_ref",
                                 "target": span[1],
                                 "message": f"code-span path ไม่พบไฟล์: {span[1]}"})

    # รวมรายการซ้ำในไฟล์เดียวกันเป็นหนึ่งบรรทัดพร้อม count
    deduped = []
    for f in findings:
        for seen in deduped:
            if seen["code"] == f["code"] and seen["target"] == f["target"]:
                seen["count"] += 1
                break
        else:
            deduped.append({**f, "count": 1})
    for f in deduped:
        f["message"] += (f" (x{f['count']})" if f["count"] > 1 else "")

    return {"file": str(path.relative_to(root)),
            "links_checked": links, "refs_checked": refs_checked,
            "external_links": external,
            "findings": deduped[:MAX_REPORT]}


def run(payload: dict) -> dict:
    if not isinstance(payload, dict):
        fail("input must be a JSON object")
    raw_dir = payload.get("dir", ".")
    if not isinstance(raw_dir, str) or not raw_dir.strip():
        fail("'dir' must be a non-empty string")
    root = Path(raw_dir.strip())
    if not root.is_dir():
        fail(f"'dir' does not exist: {root}")
    root = root.resolve()

    check_http_links = payload.get("check_http", False)
    if not isinstance(check_http_links, bool):
        fail("'check_http' must be a boolean")
    timeout = payload.get("timeout", 10)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) \
            or not 1 <= timeout <= 60:
        fail("'timeout' must be 1..60 seconds")

    files = list(md_files(root))
    if not files:
        fail(f"no markdown files under: {root}")

    text_cache = {}
    results = [scan_file(p, root, check_http_links, int(timeout), text_cache)
               for p in files]

    broken = [r for r in results if any(f["severity"] == "fail"
                                        for f in r["findings"])]
    warned = [r for r in results if any(f["severity"] == "warn"
                                        for f in r["findings"])]
    all_findings = [f for r in results for f in r["findings"]]
    fail_count = sum(1 for f in all_findings if f["severity"] == "fail")
    warn_count = sum(1 for f in all_findings if f["severity"] == "warn")

    return {
        "ok": True,
        "skill": "linkcheck",
        "verdict": "pass" if not broken else "fail",
        "dir": str(root),
        "results": [r for r in results if r["findings"]],
        "totals": {
            "files_scanned": len(results),
            "links_checked": sum(r["links_checked"] for r in results),
            "refs_checked": sum(r["refs_checked"] for r in results),
            "external_links": sum(r["external_links"] for r in results),
            "failures": fail_count,
            "warnings": warn_count,
        },
        "failures": [{"file": r["file"],
                      "findings": [f for f in r["findings"]
                                    if f["severity"] == "fail"]}
                     for r in broken],
        "next_actions": [
            f"แก้ {r['file']}: {f['message']}"
            for r in broken for f in r["findings"] if f["severity"] == "fail"
        ][:12] + [
            f"ควรแก้ {r['file']}: {f['message']}"
            for r in warned for f in r["findings"] if f["severity"] == "warn"
        ][:12],
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
