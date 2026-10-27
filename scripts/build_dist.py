#!/usr/bin/env python3
"""build_dist.py — สร้างไฟล์แจกจ่ายที่ "โหลดไปไหนก็ติดตั้งได้"

ทำไม: repo ต้องอยู่บนเครื่องถึงจะติดตั้งได้ — dist/ ทำให้พกพาเป็นไฟล์เดียว
ผลลัพธ์:
  dist/agent-skills-<version>.zip     ตัวติดตั้ง (prompt + skills + install.ps1)
  dist/MANIFEST.json                  รายการไฟล์ + sha256 (ตรวจความครบ)

ใช้:
  python scripts/build_dist.py
  python scripts/build_dist.py --version 1.0.0
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
INCLUDE = ["owner.prompt.md", "install.ps1", "README.md", "SPEC.md"]
EXCLUDE_DIRS = {"__pycache__", ".git", "dist", ".github", ".agent-loop", ".harness", "node_modules", "tests"}
EXCLUDE_SUFFIX = {".pyc", ".pyo"}
# ไฟล์ asset ที่ใหญ่และดาวน์โหลดแยกได้ (ไม่ใส่ใน zip เพื่อให้ไฟล์เล็ก)
EXCLUDE_LARGE = {".se1"}


def collect() -> list[Path]:
    files: list[Path] = []
    for name in INCLUDE:
        p = ROOT / name
        if p.exists():
            files.append(p)
    skills = ROOT / "skills"
    for p in sorted(skills.rglob("*")):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.suffix in EXCLUDE_SUFFIX or p.suffix in EXCLUDE_LARGE:
            continue
        files.append(p)
    return files


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build(version: str) -> tuple[Path, Path]:
    files = collect()
    manifest = {
        "name": "agent-skills",
        "version": version,
        "built": date.today().isoformat(),
        "files": [{"path": str(p.relative_to(ROOT)).replace("\\", "/"),
                   "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files],
    }
    DIST.mkdir(exist_ok=True)
    zip_path = DIST / f"agent-skills-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, p.relative_to(ROOT).as_posix())
        zf.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    manifest_path = DIST / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return zip_path, manifest_path


def main(argv: list[str]) -> int:
    version = argv[argv.index("--version") + 1] if "--version" in argv else "0.3.0"
    zip_path, manifest_path = build(version)
    data = zip_path.read_bytes()
    print(f"built: {zip_path}")
    print(f"  size: {len(data) / 1024:.1f} KB")
    print(f"  sha256: {hashlib.sha256(data).hexdigest()}")
    print(f"  manifest: {manifest_path}")
    print(f"  files: {len(json.loads(manifest_path.read_text(encoding='utf-8'))['files'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
