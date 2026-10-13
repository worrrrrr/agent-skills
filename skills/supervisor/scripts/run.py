#!/usr/bin/env python3
"""Deterministic engine for skill: supervisor.

ตรวจงานและให้คะแนนแบบหัวหน้างาน: รับชิ้นงาน (work) + เกณฑ์ acceptance (criteria)
แล้วตรวจความครบถ้วนแบบ keyword-coverage, ให้คะแนน/เกรด, ชี้จุดบกพร่อง,
และสรุปคำสั่งงานกลับเป็น JSON

Usage:
  python scripts/run.py '{"work": "...", "criteria": [...]}'

Input schema:
  work       string  required — ข้อความชิ้นงานที่ส่งตรวจ (อย่างน้อย 1 อักขระ)
  criteria   list    required — 1..50 เกณฑ์ เขียนเป็น string หรือ object:
             {"criterion": "...", "must_contain": [...], "must_any": [...]}
             - string            → สกัด keyword เอง ผ่านถ้าเจอ >= 50% ของ keyword
             - must_contain      → ต้องพบครบทุกตัว (contract เคร่งครัด)
             - must_any          → พบอย่างน้อย 1 ตัว
  min_score  number  optional — เกณฑ์ผ่าน 0..100 (default 60)

Exit codes: 0 = ตรวจสำเร็จ / 1 = input ไม่ครบหรือ logic error / 2 = JSON ผิดรูปแบบ
"""
import json
import re
import sys

MAX_CRITERIA = 50
LATIN_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "are", "was", "not", "has",
    "have", "will", "from", "all", "any", "you", "your", "can", "must",
    "should", "would", "into", "over", "one", "two", "use", "used",
}
THAI_STOPWORDS = {
    "มี", "ที่", "และ", "ของ", "ใน", "ไม่", "ได้", "ทำ", "กับ", "หรือ",
    "เป็น", "ต้อง", "อยู่", "แล้ว", "นี้", "นั้น", "การ", "ให้", "จะ", "ไป",
    "มา", "ก็", "ได้", "พวก", "เรา", "คุณ", "เขา", "นี้", "ครับ", "ค่ะ",
}


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "skill": "supervisor", "error": message},
                     ensure_ascii=False, indent=2))
    sys.exit(code)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def tokenize(text: str) -> list:
    """Split Thai/Latin/digit runs; drop latin stopwords and 1-char crumbs."""
    tokens = []
    for tok in re.findall(r"[0-9a-zA-Z\u0E00-\u0E7F]+", text.casefold()):
        if tok in LATIN_STOPWORDS or tok in THAI_STOPWORDS:
            continue
        is_thai = bool(re.fullmatch(r"[\u0E00-\u0E7F]+", tok))
        if len(tok) >= 2 if is_thai else len(tok) >= 3:
            tokens.append(tok)
    return tokens


def build_criterion(raw, index: int) -> dict:
    if isinstance(raw, str):
        label = raw.strip()
        if not label:
            fail(f"criteria[{index}]: empty string")
        tokens = list(dict.fromkeys(tokenize(label)))
        if not tokens:
            fail(f"criteria[{index}]: cannot extract keywords — give must_contain")
        return {"criterion": label, "must_contain": [], "must_any": tokens,
                "mode": "auto"}
    if isinstance(raw, dict):
        label = str(raw.get("criterion", "")).strip()
        if not label:
            fail(f"criteria[{index}]: missing 'criterion'")
        must_contain = raw.get("must_contain", [])
        must_any = raw.get("must_any", [])
        for key, val in (("must_contain", must_contain), ("must_any", must_any)):
            if not isinstance(val, list) or not all(
                    isinstance(x, str) and x.strip() for x in val):
                fail(f"criteria[{index}].{key}: must be a list of non-empty strings")
        must_contain = [x.strip() for x in must_contain]
        must_any = [x.strip() for x in must_any]
        if not must_contain and not must_any:
            tokens = list(dict.fromkeys(tokenize(label)))
            if not tokens:
                fail(f"criteria[{index}]: no must_contain/must_any and no "
                     "extractable keywords")
            must_any = tokens
            mode = "auto"
        else:
            mode = "explicit"
        return {"criterion": label, "must_contain": must_contain,
                "must_any": must_any, "mode": mode}
    fail(f"criteria[{index}]: must be a string or an object")


def check_criterion(crit: dict, haystack: str) -> dict:
    missing_required = [k for k in crit["must_contain"] if normalize(k) not in haystack]
    matched_required = [k for k in crit["must_contain"] if normalize(k) in haystack]
    matched_any = [k for k in crit["must_any"] if normalize(k) in haystack]
    missing_any = [k for k in crit["must_any"] if k not in matched_any]

    if crit["must_contain"]:
        passed = not missing_required
        missing = missing_required
        evidence = matched_required
        rule = "must_contain"
    else:
        coverage = len(matched_any) / len(crit["must_any"])
        passed = coverage >= 0.5
        missing = missing_any if not passed else []
        evidence = matched_any
        rule = f"must_any>={50}%"
    return {
        "criterion": crit["criterion"],
        "rule": rule,
        "passed": passed,
        "evidence": evidence,
        "missing": missing,
    }


def grade_of(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def run(payload: dict) -> dict:
    if not isinstance(payload, dict):
        fail("input must be a JSON object")
    work = payload.get("work")
    if not isinstance(work, str) or not work.strip():
        fail("'work' is required and must be a non-empty string")
    raw_criteria = payload.get("criteria")
    if not isinstance(raw_criteria, list) or not raw_criteria:
        fail("'criteria' is required and must be a non-empty list")
    if len(raw_criteria) > MAX_CRITERIA:
        fail(f"'criteria' accepts at most {MAX_CRITERIA} items")
    min_score = payload.get("min_score", 60)
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)) \
            or not 0 <= min_score <= 100:
        fail("'min_score' must be a number in 0..100")

    haystack = normalize(work)
    results = [check_criterion(build_criterion(c, i), haystack)
               for i, c in enumerate(raw_criteria)]
    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]
    score = round(100 * len(passed) / len(results))
    verdict = "approve" if score >= min_score else "revise"

    return {
        "ok": True,
        "skill": "supervisor",
        "score": score,
        "grade": grade_of(score),
        "verdict": verdict,
        "min_score": min_score,
        "criteria_results": results,
        "gaps": [{"criterion": r["criterion"], "missing": r["missing"]}
                 for r in failed],
        "next_actions": [f"แก้เกณฑ์: {r['criterion']}"
                         + (f" (ขาด: {', '.join(r['missing'])})" if r["missing"] else "")
                         for r in failed],
        "stats": {
            "criteria_total": len(results),
            "criteria_passed": len(passed),
            "criteria_failed": len(failed),
            "work_chars": len(work),
            "work_words": len(work.split()),
        },
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
