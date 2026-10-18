#!/usr/bin/env python3
"""w8m engine — World 8 Models: กรอบวิเคราะห์ปัญหา/การตัดสินใจ 8 แบบ

JSON-in / JSON-out ทั้งหมด (ทน BOM, envelope เดียวกับ skills/math):

  python run.py '{"op":"list"}'
  python run.py '{"op":"show","id":"inversion"}'
  python run.py '{"op":"plan","problem":"จะโปรโมตพนักงานดีไหม","k":4}'
  python run.py '{"op":"analyze","problem":"..."}'                     # scaffold
  python run.py '{"op":"analyze","problem":"...","answers":{"inversion":"..."}}'
  python run.py '{"op":"report","problem":"...","answers":{...}}'      # markdown

Ops: list | show | plan | analyze | report

หลักการของ engine: คิดเองไม่ได้ (ไม่ใช่ LLM) — หน้าที่คือ
เลือกโมเดลที่เหมาะกับโจทย์, แจกโครงคำถาม, ตรวจว่าคำตอบครอบคลุมหรือยัง,
และประกอบ markdown report จากคำตอบที่ agent กรอกมา (ไม่แต่งคำตอบแทน)
"""
import json
import re
import sys

ENGINE_VERSION = "1.0.0"

# ลำดับ = ลำดับจัดอันดับเมื่อคะแนนเท่ากัน
MODELS = [
    {
        "id": "first-principles",
        "name": "First Principles",
        "name_th": "แยกสู่หลักการพื้นฐาน",
        "one_liner": "รื้อโจทย์ลงเป็นข้อเท็จจริงที่ตรวจสอบได้ แล้วประกอบใหม่ แทนการยืมคำตอบของคนอื่น",
        "when": "โจทย์ดูคลุมเครือ เต็มไปด้วยคำศัพท์วงใน หรือมีคนบอกว่า 'ของแบบนี้เขาทำกันอย่างนี้'",
        "questions": [
            "ข้อเท็จจริงที่แน่นอนและตรวจสอบได้มีอะไรบ้าง (ไม่ใช่ความเห็น)",
            "ข้อสมมติใดที่ถ้าปล่อยทิ้งไว้ โครงสร้างทั้งหมดพัง",
            "ถ้าต้องสร้างวิธีแก้ใหม่ตั้งแต่ศูนย์โดยไม่สนของเดิม จะหน้าตาเป็นอย่างไร",
            "ต้นทุน/ข้อจำกัดจริง (ฟิสิกส์ งบ เวลา) คืออะไร",
        ],
        "steps": [
            "เขียนโจทย์เป็นประโยคเดียวที่ไม่มีศัพท์วงใน",
            "ไล่สมมติฐานทั้งหมด แล้วติดแท็กว่าข้อไหนตรวจสอบได้",
            "ตัดสมมติฐานที่ตรวจสอบไม่ได้ออก แล้วสร้างวิธีแก้จากที่เหลือ",
            "เทียบวิธีแก้ที่ได้กับของเดิม: ต่างเพราะหลักการ หรือแค่ต่างเพราะเคยชิน",
        ],
        "deliverable": ["ข้อเท็จจริงที่ใช้", "สมมติฐานที่ตัดทิ้ง", "วิธีแก้ที่ประกอบใหม่"],
        "red_flags": [
            "เอา 'ทุกคนทำแบบนี้' มาเป็นข้อเท็จจริง",
            "รื้อหมดทุกอย่างทั้งที่ข้อจำกัดจริงไม่ได้บังคับ",
        ],
        "tags": ["first principle", "หลักการพื้นฐาน", "แก่น", "สมมติ", "assumption",
                 "รื้อ", "rebuild", "ต้นทุนจริง", "ของแบบนี้เขาทำกัน"],
    },
    {
        "id": "inversion",
        "name": "Inversion",
        "name_th": "คิดย้อนกลับจากความล้มเหลว",
        "one_liner": "ถามก่อนว่า 'ทำอย่างไรถึงจะพัง' แล้วเลี่ยงสิ่งนั้น — มักง่ายกว่าการหาวิธีชนะ",
        "when": "ต้องการป้องกันความเสี่ยง, ทำ pre-mortem, หรือปัญหาหาทางสำเร็จไม่เจอ",
        "questions": [
            "ทำอะไรถึงจะรับประกันว่าโครงการนี้ล้มเหลวแน่ ๆ",
            "ความล้มเหลวแบบไหนที่เจ็บเกินจะกู้ (non-recoverable)",
            "ตอนนี้กำลังเดินเข้าไปในความล้มเหลวนั้นอยู่หรือเปล่า",
            "หยุด/เลิก ตั้งแต่เมื่อไรถึงจะยังถือว่าทัน",
        ],
        "steps": [
            "เขียนรายการ 'วิธีทำให้พัง' ให้ครบและตรงไปตรงมาที่สุด",
            "จัดอันดับว่าข้อไหนพาไปสู่ความเสียหายที่กู้ไม่ได้",
            "แปลงแต่ละข้อเป็นกฎ/เช็คลิสต์ที่ป้องกันได้จริง",
            "ตั้งสัญญาณเตือน (trigger) ที่บอกว่ากำลังเดินเข้าไปในข้อนั้น",
        ],
        "deliverable": ["วิธีทำให้พัง", "ความเสี่ยงที่กู้ไม่ได้", "กฎป้องกัน + สัญญาณเตือน"],
        "red_flags": [
            "ไล่แต่ความเสี่ยงเล็ก ๆ โดยไม่แตะข้อที่เจ็บจริง",
            "ป้องกันจนไม่กล้าลงมือทำอะไรเลย",
        ],
        "tags": ["invert", "ย้อนกลับ", "ล้มเหลว", "fail", "premortem", "pre-mortem",
                 "ป้องกัน", "หลีกเลี่ยง", "ความเสี่ยง", "อะไรจะผิดพลาด"],
    },
    {
        "id": "second-order",
        "name": "Second-Order Thinking",
        "name_th": "คิดถึงผลกระทบชั้นสอง",
        "one_liner": "และแล้วไง (and then what?) — ผลลัพธ์ของผลลัพธ์ ซึ่งมักย้อนกลับมาทำลายคำตอบชั้นแรก",
        "when": "มีนโยบาย/มาตรการ/การเปลี่ยนแปลงที่คนได้ประโยชน์ทันที แต่อาจมีผลข้างเคียง",
        "questions": [
            "ผลชั้นแรกคืออะไร ใครได้ใครเสียทันที",
            "ผลชั้นสอง: คนที่ได้/เสียจะปรับตัวอย่างไร เมื่อรู้ว่าจะเกิดผลชั้นแรก",
            "ผลชั้นสามที่ตามมาแบบไม่ตั้งใจคืออะไร",
            "ผลเสียชั้นสองมีน้ำหนักมากพอจะกลืนผลชั้นแรกหรือไม่",
        ],
        "steps": [
            "วาดสายผลเป็น 3 ชั้น: การกระทำ → ปฏิกิริยาของคน → ผลระยะยาว",
            "ทำเครื่องหมายจุดที่คนเริ่มปรับตัว (จุดนั้นเปลี่ยนผลทั้งหมด)",
            "ประเมินว่าชั้นไหนมีขนาดใหญ่สุด",
            "ตัดสินใจใหม่โดยเอาผลชั้นสองมารวมในการคิดชั้นแรก",
        ],
        "deliverable": ["ผลชั้นแรก", "ผลชั้นสอง/สาม", "จุดที่คนปรับตัว", "ข้อสรุปที่รวมผลข้างเคียง"],
        "red_flags": [
            "หยุดคิดที่ผลชั้นแรกเพราะดูดี",
            "ประเมินผลข้างเคียงแบบเดาโดยไม่มีกลไกอธิบาย",
        ],
        "tags": ["ผลกระทบ", "ต่อเนื่อง", "ripple", "consequence", "side effect",
                 "นโยบาย", "ระยะยาว", "long term", "domino", "ทวี", "และแล้วไง"],
    },
    {
        "id": "expected-value",
        "name": "Expected Value",
        "name_th": "ค่าคาดหวัง",
        "one_liner": "ผลลัพธ์ × ความน่าจะเป็น — ตัดสินด้วยค่าเฉลี่ยของทุกครั้งที่จะเกิด ไม่ใช่ครั้งนี้ครั้งเดียว",
        "when": "มีตัวเลือกเสี่ยงหลายแบบ ต้องเทียบการเดิมพัน ลงทุน หรือเลือกเส้นทางที่ผลไม่แน่นอน",
        "questions": [
            "ผลลัพธ์ที่เป็นไปได้แต่ละแบบคืออะไร และคุ้มค่าแค่ไหน (ตัวเลข)",
            "ความน่าจะเป็นของแต่ละแบบมาจากไหน (ประเมิน/สถิติ/เดา)",
            "ค่าคาดหวังรวมเป็นบวกหรือลบ เมื่อหักต้นทุน",
            "ถ้าทำซ้ำ 100 ครั้ง ผลเฉลี่ยคืออะไร — ครั้งนี้ครั้งเดียวต่างกันตรงไหน",
        ],
        "steps": [
            "ไล่ผลลัพธ์ทั้งหมดพร้อมมูลค่า (รวมศูนย์/ลบ)",
            "ใส่ความน่าจะเป็น แล้วทำเครื่องหมายว่าตัวเลขไหนประเมินเอง",
            "คำนวณ EV = Σ (p × v) และหักต้นทุน",
            "เช็คข้อจำกัด: ขาดทุนกู้ไม่ได้ไหม (ไม่ใช่แค่ EV เป็นบวก = ทำ)",
        ],
        "deliverable": ["ตารางผล × ความน่าจะเป็น", "ค่าคาดหวังสุทธิ", "ข้อจำกัดด้านเงิน/เวลา", "การตัดสินใจ"],
        "red_flags": [
            "ให้ความน่าจะเป็นแบบมั่นใจเกินจริงโดยไม่มีหลัก",
            "ลืมต้นทุนคงที่ หรือลืมว่าเจ็บครั้งเดียวไม่กู้ได้",
        ],
        "tags": ["ค่าคาดหวัง", "expected value", "ev", "ความน่าจะเป็น", "probability",
                 "ลงทุน", "กำไร", "ขาดทุน", "roi", "bet", "เสี่ยง", "คุ้มไหม"],
    },
    {
        "id": "base-rate",
        "name": "Base Rate",
        "name_th": "เริ่มจากอัตราฐานของกลุ่ม",
        "one_liner": "ก่อนใช้เรื่องเล่าของกรณีเฉพาะ ให้ดูสถิติของกลุ่มก่อน — กรณีเฉพาะมักไม่ใช่เรื่องปกติ",
        "when": "มีเคสตัวอย่างที่น่าประทับใจมาขายไอเดีย หรือต้องทำนายโอกาสสำเร็จ",
        "questions": [
            "กลุ่มนี้ (industry/team/ประเภทโปรเจกต์) สำเร็จกี่เปอร์เซ็นต์",
            "เคสที่ยกมาใกล้ฐานของกลุ่มแค่ไหน หรือเป็นผู้รอดที่ถูกเล่าซ้ำ",
            "พอปรับด้วยข้อมูลเฉพาะของกรณีนี้แล้ว โอกาสเปลี่ยนไปแค่ไหน",
            "ถ้าไม่รู้อะไรเกี่ยวกับเคสนี้เลย จะทายอะไรจากสถิติล้วน",
        ],
        "steps": [
            "หาอัตราฐานจากข้อมูลกลุ่ม (ไม่ใช่จากเคสที่ถูกเล่า)",
            "ปรับด้วยข้อมูลเฉพาะของกรณี แล้วบอกช่วงความไม่แน่นอน",
            "บอกชัดว่าตัวเลขไหนมาจากสถิติ ไหนมาจาก judgement",
            "ถ้าอัตราฐานต่ำมาก ต้องมีเหตุผลที่ดีมากถึงจะฝืน",
        ],
        "deliverable": ["อัตราฐานของกลุ่ม", "การปรับด้วยข้อมูลเฉพาะ", "ช่วงประมาณการ", "คำทำนาย"],
        "red_flags": [
            "ใช้ survivorship bias เป็นอัตราฐาน",
            "จำเรื่องเคสตัวอย่างได้ดีกว่าสถิติ",
        ],
        "tags": ["base rate", "อัตราฐาน", "สถิติ", "ค่าเฉลี่ย", "average", "กลุ่มตัวอย่าง",
                 "benchmark", "อัตราส่วน", "โอกาสสำเร็จ", "แนวโน้ม", "sample"],
    },
    {
        "id": "occam",
        "name": "Occam's Razor",
        "name_th": "มีดโกนออกัม — เลือกคำอธิบายที่สมมติน้อยสุด",
        "one_liner": "เมื่อสองคำอธิบายอธิบายได้เท่ากัน ให้เลือกอันที่ต้องสมมติเพิ่มน้อยกว่า",
        "when": "มีสมมติฐานแข่งกันหลายอัน หรือเริ่มต่อเรื่องซับซ้อนขึ้นเรื่อย ๆ โดยไม่จำเป็น",
        "questions": [
            "มีคำอธิบาย/ทางออกแบบใดบ้าง และแต่ละอันต้องสมมติเพิ่มอะไร",
            "คำอธิบายไหนอธิบายข้อเท็จจริงชุดเดียวกันได้ครบด้วยสมมติฐานน้อยสุด",
            "มีการเพิ่มความซับซ้อนตรงไหนที่ยังไม่มีหลักฐานบังคับ",
            "ถ้าต้องอธิบายเรื่องนี้ใน 3 ประโยค จะพูดอย่างไร",
        ],
        "steps": [
            "ไล่คำอธิบาย/ทางเลือกทั้งหมด",
            "นับสมมติฐานของแต่ละอัน (รวมสมมติฐานที่ซ่อนอยู่)",
            "ตัดอันที่ซับซ้อนกว่าแต่ไม่อธิบายได้ดีกว่า",
            "เก็บความซับซ้อนไว้ก็ต่อเมื่อมีหลักฐานบังคับโดยตรง",
        ],
        "deliverable": ["ทางเลือกที่เทียบกัน", "จำนวนสมมติฐานของแต่ละอัน", "ทางเลือกที่ถูกเลือก + เหตุผล"],
        "red_flags": [
            "เข้าใจผิดว่าต้องเลือกคำตอบที่สั้นเสมอ (บางเรื่องซับซ้อนจริง)",
            "ซ่อนสมมติฐานไว้เพื่อให้ดูเรียบง่าย",
        ],
        "tags": ["occam", "ง่าย", "เรียบง่าย", "ซับซ้อน", "hypothesis", "สมมติฐาน",
                 "อธิบาย", "simpler", "เทียบทางเลือก", "แบบจำลอง"],
    },
    {
        "id": "feedback-loop",
        "name": "Feedback Loops",
        "name_th": "วงจรสะท้อน (เสริมแรง / ถดถอย) + ความหน่วง",
        "one_liner": "ระบบมีวงจรย้อนกลับ: สิ่งที่ทำจะไปเร่งหรือไปหัก ยิ่งมี delay ยิ่งพังง่าย",
        "when": "ปัญหาเป็นระบบ มีตัวแปรที่ตอบสนองต่อกัน หรือมาตรการที่เคยได้ผลกลับได้ผลน้อยลง",
        "questions": [
            "วงจรไหนเสริมแรง (more begets more) และวงจรไหนถดถอย (หักล้างกัน)",
            "จุดหน่วง (delay) อยู่ตรงไหน — ระหว่างกระทำกับผลลัพธ์",
            "ยิ่งเร่งวงจรเสริมแรง จะเกิด overshoot / พัง ตอนไหน",
            "ตัวชี้วัดตัวไหนบอกสัญญาณก่อนเกิดจริง (leading vs lagging)",
        ],
        "steps": [
            "วาดแผนผังตัวแปรและลูกศร (เพิ่ม/ลด) รวมจุดหน่วง",
            "แยกว่าวงจรไหนครอบงำ ณ ช่วงเวลานี้",
            "จำลองในหัวว่าถ้าดันคันนี้ 3 เดือนจะเกิดอะไร",
            "ออกแบบจุดควบคุม: ตัดวงจรเสริมแรง หรือเพิ่ม damping",
        ],
        "deliverable": ["แผนผังวงจร", "จุดหน่วง", "จุดควบคุมที่เสนอ", "สัญญาณเตือนล่วงหน้า"],
        "red_flags": [
            "แก้ที่ปลายเหตุโดยไม่แต่วงจรที่เลี้ยงปัญหา",
            "ประเมินผลทันทีทั้งที่ระบบมี delay",
        ],
        "tags": ["feedback", "วงจร", "สะท้อน", "loop", "เสริมแรง", "ถดถอย", "delay",
                 "หน่วง", "system", "ระบบ", "cycle", "vicious", "overshoot"],
    },
    {
        "id": "margin-of-safety",
        "name": "Margin of Safety",
        "name_th": "ขอบเผื่อความปลอดภัย",
        "one_liner": "อย่าออกแบบให้ชิดขีดจำกัด — เผื่อส่วนต่างไว้เพราะค่าประมาณของเราผิดเสมอ",
        "when": "ตัวเลขที่ใช้ตัดสินใจเป็นการประมาณ หรือความผิดพลาดมีราคาแพง/กู้ไม่ได้",
        "questions": [
            "ถ้าค่าประมาณผิดไป 20–50% แผนยังรอดไหม",
            "เผื่อตรงไหนได้บ้าง: เวลา งบ จำนวนคน ความจุ",
            "จุดพังของระบบอยู่ตรงไหน และตอนนี้ห่างแค่ไหน",
            "ถ้าผิดพลาดครั้งเดียวแล้วจบ จะลดขนาดการผจภัยลงได้อย่างไร",
        ],
        "steps": [
            "หาจุดพัง (breaking point) ของแผน",
            "ประมาณค่าที่ใช้ตัดสินใจ แล้วทำ stress test -20%/-50%",
            "กำหนดขอบเผื่อเป็นตัวเลข ไม่ใช่คำว่า 'เผื่อไว้หน่อย'",
            "ถ้าขอบเผื่อกินพื้นที่หมด ให้ลดขนาดแผน ไม่ใช่ลดขอบเผื่อ",
        ],
        "deliverable": ["จุดพัง", "ค่าประมาณที่ใช้ + ความคลาดเคลื่อน", "ขอบเผื่อเป็นตัวเลข", "แผนเมื่อสมมติว่าประมาณผิด"],
        "red_flags": [
            "ใช้ขอบเผื่อ 0% เพราะ 'แบบจำลองบอกว่าแน่นอน'",
            "ตัดขอบเผื่อออกเมื่องบไม่พอ (เป็นจุดที่มักพัง)",
        ],
        "tags": ["margin", "ขอบเผื่อ", "safety", "ปลอดภัย", "buffer", "สำรอง", "เผื่อ",
                 "tolerance", "stress test", "เผื่อไว้หน่อย", "งบไม่พอ"],
    },
]

BY_ID = {m["id"]: m for m in MODELS}
DEFAULT_SET = ["first-principles", "inversion", "second-order", "occam"]


def _norm(s: str) -> str:
    return (s or "").lower()


def _tag_hit(tag: str, low: str) -> bool:
    """tag ASCII ต้องตรงทั้งคำ (กัน 'roi' ชน 'android') แต่รับ plural/hyphen;
    ภาษาอื่นใช้ substring"""
    t = _norm(tag).replace("-", " ")
    if not t:
        return False
    if t.isascii():
        p = low.replace("-", " ")
        return re.search(rf"(?<![a-z0-9]){re.escape(t)}(?:e?s)?(?![a-z0-9])", p) is not None
    return t in low


def _rank(problem: str, k: int):
    """จัดอันดับโมเดลด้วยจำนวน tag ที่ไปปรากฏในโจทย์ (heuristic, ไม่ใช่ LLM)"""
    low = _norm(problem)
    scored = []
    for i, m in enumerate(MODELS):
        hits = sorted({t for t in m["tags"] if _tag_hit(t, low)})
        scored.append((-len(hits), i, m, hits))
    scored.sort(key=lambda t: (t[0], t[1]))
    return scored


def _select(problem: str, ids=None, k: int = 4):
    """คืน (models, matched_tags_per_model, fallback_flag) เรียงตามคะแนน tag"""
    if ids:
        unknown = [i for i in ids if i not in BY_ID]
        if unknown:
            raise ValueError(
                f"โมเดลไม่ถูกต้อง: {unknown} — ใช้ได้: {list(BY_ID)}")
        return [BY_ID[i] for i in ids], {i: [] for i in ids}, False
    k = max(2, min(int(k), len(MODELS)))
    scored = _rank(problem, len(MODELS))
    matched = [s for s in scored if s[0] < 0][:k]
    fallback = not matched
    picked = list(matched)
    if fallback:
        picked = [(0, i, BY_ID[x], []) for i, x in enumerate(DEFAULT_SET)]
    if len(picked) < k:  # เติมโมเดลที่คะแนนเป็นศูนย์ให้ครบ k (เรียงตาม tag ก่อน)
        have = {s[2]["id"] for s in picked}
        picked += [s for s in scored if s[0] == 0 and s[2]["id"] not in have]
    picked = picked[:k]
    return ([s[2] for s in picked],
            {s[2]["id"]: s[3] for s in picked},
            fallback)


def _coverage(models, answers):
    if not isinstance(answers, dict):
        raise ValueError("answers ต้องเป็น object: {\"<model-id>\": ...}")
    unknown = [k for k in answers if k not in BY_ID]
    if unknown:
        raise ValueError(f"answers มีโมเดลที่ไม่รู้จัก: {unknown}")
    answered, missing, empty = [], [], {}
    for m in models:
        mid = m["id"]
        if mid not in answers:
            missing.append(mid)
            continue
        a = answers[mid]
        if isinstance(a, dict):
            blanks = [f for f in m["deliverable"]
                      if not str(a.get(f, "") or "").strip()]
            if not any(str(v or "").strip() for v in a.values()):
                missing.append(mid)
            elif blanks:
                empty[mid] = blanks
                answered.append(mid)
            else:
                answered.append(mid)
        elif str(a or "").strip():
            answered.append(mid)
        else:
            missing.append(mid)
    return {
        "selected": [m["id"] for m in models],
        "answered": answered,
        "missing": missing,
        "empty_fields": empty,
        "ignored": sorted(k for k in answers if k not in {m["id"] for m in models}),
        "complete": not missing and not empty,
        "progress": f"{len(answered)}/{len(models)}",
    }


def _scaffold(m):
    return {
        "id": m["id"],
        "name": m["name"],
        "name_th": m["name_th"],
        "one_liner": m["one_liner"],
        "questions": m["questions"],
        "steps": m["steps"],
        "deliverable": m["deliverable"],
        "red_flags": m["red_flags"],
    }


def op_list():
    return {
        "count": len(MODELS),
        "models": [
            {"id": m["id"], "name": m["name"], "name_th": m["name_th"],
             "one_liner": m["one_liner"], "tags": m["tags"]}
            for m in MODELS
        ],
    }


def op_show(mid: str):
    if mid not in BY_ID:
        raise ValueError(f"ไม่มีโมเดล '{mid}' — ใช้ได้: {list(BY_ID)}")
    return BY_ID[mid]


def op_plan(problem: str, ids=None, k: int = 4):
    models, hits_by_id, fallback = _select(problem, ids, k)
    picked = [m["id"] for m in models]
    if ids:
        note = f"ใช้โมเดลที่ระบุเอง: {', '.join(picked)}"
    elif fallback:
        note = (f"ไม่พบ tag ในโจทย์ จึงใช้ชุดเริ่มต้น {', '.join(picked)} "
                f"(k={len(picked)})")
    else:
        hit = [i for i in picked if hits_by_id[i]]
        fill = [i for i in picked if not hits_by_id[i]]
        note = f"จับคู่จาก tag: {', '.join(hit) or '-'}"
        if fill:
            note += f"; เติมให้ครบ {len(picked)}: {', '.join(fill)}"
        note += " — ระบุ models เองได้ถ้าไม่ตรงใจ"
    return {
        "problem": problem,
        "matched_by_tags": bool(not ids and not fallback),
        "note": note,
        "models": [
            {
                "id": m["id"], "name": m["name"], "name_th": m["name_th"],
                "matched_tags": hits_by_id[m["id"]],
                "why": m["one_liner"],
                "questions": m["questions"],
                "deliverable": m["deliverable"],
            }
            for m in models
        ],
    }


def op_analyze(problem: str, ids=None, answers=None, k: int = 4):
    models, _, _ = _select(problem, ids, k)
    out = {
        "problem": problem,
        "how_to": ("ตอบ questions ของแต่ละโมเดลตามข้อเท็จจริงของโจทย์ แล้วส่งกลับเป็น "
                   "answers: {\"<model-id>\": {\"<deliverable>\": \"...\"}} "
                   "หรือ answers: {\"<model-id>\": \"ข้อความอิสระ\"} "
                   "จากนั้นยิง op=report เพื่อประกอบรายงาน"),
        "models": [_scaffold(m) for m in models],
    }
    if answers is not None:
        out["coverage"] = _coverage(models, answers)
    return out


def _render_answer(m, a):
    lines = []
    if isinstance(a, dict):
        for f in m["deliverable"]:
            v = str(a.get(f, "") or "").strip()
            lines.append(f"- **{f}**: {v if v else '_(ยังไม่ตอบ)_'}")
        for k, v in a.items():  # ฟิลด์เสริมที่ agent เพิ่มเอง
            if k not in m["deliverable"] and str(v or "").strip():
                lines.append(f"- **{k}**: {v}")
    else:
        for ln in str(a or "").strip().splitlines():
            lines.append(f"- {ln}" if not ln.startswith("-") else ln)
    return "\n".join(lines)


def op_report(problem: str, answers: dict, ids=None, title=None, k: int = 4):
    models, _, _ = _select(problem, ids, k)
    cov = _coverage(models, answers)
    secs, n = [], 0
    for m in models:
        a = answers.get(m["id"])
        n += 1
        mark = "✓" if m["id"] in cov["answered"] and m["id"] not in cov["empty_fields"] else "…"
        secs.append(
            f"## {n}. {m['name']} ({m['name_th']}) {mark}\n\n"
            f"> {m['one_liner']}\n\n"
            + (_render_answer(m, a) if a is not None
               else "_ยังไม่ได้ตอบ — ดูคำถามใน scaffold ของ op=analyze_\n")
        )
    gaps = ([f"{g}: ยังไม่ตอบ" for g in cov["missing"]]
            + [f"{mid}: ยังไม่ตอบ {', '.join(fs)}"
               for mid, fs in cov["empty_fields"].items()]
            + [f"{mid}: มีคำตอบแต่ไม่ได้อยู่ในโมเดลที่เลือก"
               for mid in cov["ignored"]])
    body = "\n\n".join(secs)
    tail = ("## สรุปความครอบคลุม\n\n"
            f"- ตอบแล้ว {cov['progress']} โมเดล\n"
            + (f"- ช่องว่าง: {'; '.join(gaps)}\n" if gaps
               else "- ครบทุกโมเดลที่เลือก\n"))
    md = (f"# {title or 'บทวิเคราะห์: ' + problem}\n\n"
          f"**ปัญหา**: {problem}\n\n{body}\n\n{tail}")
    return {"markdown": md, "coverage": cov, "gaps": gaps}


def run(p: dict):
    op = p.get("op", "list")
    if op == "list":
        return op_list()
    if op == "show":
        return op_show(p["id"])
    if op == "plan":
        return op_plan(p.get("problem", ""), p.get("models"), p.get("k", 4))
    if op == "analyze":
        return op_analyze(p.get("problem", ""), p.get("models"),
                          p.get("answers"), p.get("k", 4))
    if op == "report":
        return op_report(p.get("problem", ""), p.get("answers") or {},
                         p.get("models"), p.get("title"), p.get("k", 4))
    raise ValueError(f"unknown op: {op} (ใช้ได้: list | show | plan | analyze | report)")


def main() -> None:
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    # ทน BOM (PowerShell 5.1 / ไฟล์ที่สร้างบน Windows)
    if raw and raw[0] == "\ufeff":
        raw = raw.lstrip("\ufeff")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}, ensure_ascii=False))
        sys.exit(2)
    if not isinstance(payload, dict):
        print(json.dumps({"error": "payload ต้องเป็น JSON object เช่น "
                                   '{"op":"list"}'}, ensure_ascii=False))
        sys.exit(2)
    try:
        print(json.dumps({"ok": True, "engine": ENGINE_VERSION,
                          "result": run(payload)}, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
