"""Thai-language chart interpreter.

Imports the calculation engines from ``astrology.py`` and turns their raw
output into a plain-text Thai reading covering all four systems:

    1. ปาจื่อ / สี่เสา   (BaZi)
    2. โหราศาสตร์ตะวันตก (Western)
    3. โหราศาสตร์ภารตะ   (Vedic)
    4. ฮิวแมนดีไซน์       (Human Design)

Usage:
    python reading.py 1992 8 8 16 49 6.53995 101.29 7 [m|f]
    WOR_INPUT='{"year":1992,...}' python reading.py

The engines only *calculate*; this file adds the interpretation layer.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

from astrology import (
    BaZiEngine,
    WesternEngine,
    VedicEngine,
    HDEngine,
    HEAVENLY_STEMS,
    EARTHLY_BRANCHES,
)
import swisseph as swe


# ======================================================================
# Ephemeris path — prefer the bundled assets/*.se1
# ======================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def default_ephe_path() -> str:
    for cand in (
        os.path.join(SCRIPT_DIR, "..", "assets"),
        os.path.join(SCRIPT_DIR, "..", "data"),
    ):
        if os.path.isdir(cand) and any(f.endswith(".se1") for f in os.listdir(cand)):
            return cand
    return "data/ephe"


# ======================================================================
# Thai lookup tables
# ======================================================================

ELEMENT_TH = {"Wood": "ไม้", "Fire": "ไฟ", "Earth": "ดิน", "Metal": "ทอง", "Water": "น้ำ"}

STEM_TH = {
    "Jia": "เจี่ย", "Yi": "อี่", "Bing": "ปิ่ง", "Ding": "ติง", "Wu": "อู้",
    "Ji": "จี่", "Geng": "เกิง", "Xin": "ซิน", "Ren": "เหริน", "Gui": "กุ้ย",
}

DAY_MASTER_TH = {
    "Wood": "ไม้ — เติบโต ยืดหยุ่น มีเมตตา ชอบช่วยเหลือ ชอบวางแผนระยะยาว",
    "Fire": "ไฟ — ร้อนแรง มีเสน่ห์ มั่นใจ ชอบแสดงออก อารมณ์เร็วแต่ใจกว้าง",
    "Earth": "ดิน — มั่นคง น่าเชื่อถือ อดทน เป็นที่พึ่งของคนอื่น อาจยึดติดกับแบบเดิม",
    "Metal": "ทอง — มีระเบียบ เด็ดขาด ยุติธรรม จริงจัง ยึดหลักการ",
    "Water": "น้ำ — ฉลาด ปรับตัวเก่ง ลึกซึ้ง ชอบเรียนรู้ อ่อนไหวแต่ยืดหยุ่น",
}

POLARITY_TH = {
    "yang": "หยาง (陽) — แสดงออก บุก ริเริ่ม ตรงไปตรงมา",
    "yin": "หยิน (陰) — รับ ประณีต ยืดหยุ่น ละเอียดอ่อน",
}

DEITY_TH = {
    "比肩": "เพื่อน/ตัวเอง (เป่ยเจียน) — พึ่งพาตนเอง มีพี่น้อง-เพื่อนฝูง แข่งขัน",
    "劫财": "แย่งทรัพย์ (เจี๋ยไฉ) — คู่แข่ง ชอบเสี่ยง มีโอกาสเสียทรัพย์",
    "食神": "เทพโภชนาการ (สือเสิน) — พรสวรรค์ ความสุข การแสดงออกนุ่มนวล",
    "伤官": "ขุนนางพิฆาต (ซางกวน) — อัจฉริยะ ปฏิวัติ แสดงเก่ง ลิ้นคม",
    "偏财": "ทรัพย์อ้อม (เพียนไฉ) — โชคลาภลอย โอกาสเข้าสังคม บิดา",
    "正财": "ทรัพย์ตรง (เจิ้งไฉ) — รายได้มั่นคง ขยัน คู่ครอง (ชาย)",
    "七杀": "เจ็ดสังหาร (ชีซา) — แรงกดดัน อำนาจ วินัย ความเสี่ยง",
    "正官": "ขุนนางตรง (เจิ้งกวน) — หน้าที่ ระเบียบ ชื่อเสียง คู่ครอง (หญิง)",
    "偏印": "印อ้อม (เพียนอิ่น) — เรียนนอกกรอบ สัญชาตญาณ สันโดษ",
    "正印": "印ตรง (เจิ้งอิ่น) — ผู้สนับสนุน การศึกษา มารดา",
}

DEITY_CODE = {
    "比肩": "FR", "劫财": "RW", "食神": "EG", "伤官": "HO",
    "偏财": "IW", "正财": "DW", "七杀": "7K", "正官": "DO",
    "偏印": "IR", "正印": "DR",
}


def _fmt_deity(label: str) -> str:
    return f"{DEITY_TH.get(label, label)} [{DEITY_CODE.get(label, '?')}]"


PILLAR_TH = {
    "year": "เสาปี — บรรพบุรุษ ชีวิตวัยเด็ก ภาพลักษณ์ต่อสังคม",
    "month": "เสาเดือน — พ่อแม่ อาชีพ สภาพแวดล้อม (เสาที่มีพลังที่สุด)",
    "day": "เสาวัน — ตัวตน (ก้าน) และคู่ครอง (ก้านดิน)",
    "hour": "เสาชั่วโมง — บุตร ชีวิตบั้นปลาย ความมุ่งหวังในใจ",
}

ELEMENT_ADVICE_TH = {
    "Wood": "เสริมด้านความคิดสร้างสรรค์ การวางแผนระยะยาว และการผูกมิตร",
    "Fire": "เสริมด้านชื่อเสียง การแสดงออก และพลังทางสังคม",
    "Earth": "เสริมด้านความมั่นคง การเงินระยะยาว และสุขภาพ",
    "Metal": "เสริมด้านวินัย การบริหารเงิน และความชัดเจนเด็ดขาด",
    "Water": "เสริมด้านสติปัญญา การเรียนรู้ และความยืดหยุ่น",
}

SIGN_TH = {
    "Aries": "เมษ", "Taurus": "พฤษภ", "Gemini": "เมถุน", "Cancer": "กรกฎ",
    "Leo": "สิงห์", "Virgo": "กันย์", "Libra": "ตุลย์", "Scorpio": "พิจิก",
    "Sagittarius": "ธนู", "Capricorn": "มังกร", "Aquarius": "กุมภ์", "Pisces": "มีน",
}

PLANET_TH = {
    "Sun": ("อาทิตย์", "ตัวตน แก่นแท้ จุดมุ่งหมายของชีวิต"),
    "Moon": ("จันทร์", "อารมณ์ สัญชาตญาณ ความต้องการในใจ"),
    "Mercury": ("พุธ", "ความคิด การสื่อสาร การเรียนรู้"),
    "Venus": ("ศุกร์", "ความรัก คุณค่า ศิลปะ การเงิน"),
    "Mars": ("อังคาร", "พลังขับ ความกล้า การลงมือ"),
    "Jupiter": ("พฤหัสบดี", "การขยายตัว โชคลาภ ความเชื่อ"),
    "Saturn": ("เสาร์", "วินัย ข้อจำกัด หน้าที่ และเวลา"),
    "Uranus": ("ยูเรนัส", "นวัตกรรม ปฏิวัติ การเปลี่ยนแปลงฉับพลัน"),
    "Neptune": ("เนปจูน", "จินตนาการ ความฝัน เมตตา ภาพลวง"),
    "Pluto": ("พลูโต", "อำนาจ การเปลี่ยนแปลงเชิงลึก การเกิดใหม่"),
}

HOUSE_TH = [
    "ตัวตน บุคลิก ร่างกาย",
    "การเงิน ทรัพย์สิน คุณค่าในตัวเอง",
    "การสื่อสาร พี่น้อง การเดินทางสั้น",
    "บ้าน รากเหง้า ครอบครัว",
    "ความรัก ความสร้างสรรค์ บุตร การเล่น",
    "การงานประจำ สุขภาพ กิจวัตร",
    "คู่ครอง หุ้นส่วน ศัตรูที่เปิดเผย",
    "ทรัพย์ร่วม ความใกล้ชิด การเปลี่ยนแปลง",
    "ปรัชญา การศึกษาสูง การเดินทางไกล",
    "อาชีพ ชื่อเสียง บทบาทต่อสังคม",
    "เพื่อน กลุ่ม ความหวังในอนาคต",
    "จิตใต้สำนึก ความสันโดษ จุดจบ",
]

ASPECT_TH = {
    "Conjunction": "รวมพลัง", "Sextile": "เกื้อหนุน", "Square": "ขัดแย้ง",
    "Trine": "กลมกลืน", "Quincunx": "ต้องปรับตัว", "Opposition": "ตรงข้าม",
}

RASHI_TH = {
    "Mesha": "เมษ", "Vrishabha": "พฤษภ", "Mithuna": "เมถุน", "Karka": "กรกฎ",
    "Simha": "สิงห์", "Kanya": "กันย์", "Tula": "ตุล", "Vrishchika": "พิจิก",
    "Dhanu": "ธนู", "Makara": "มังกร", "Kumbha": "กุมภ์", "Meena": "มีน",
}

NAKSHATRA_TH = {
    "Ashwini": "เริ่มต้นเร็ว กล้าบุก มีพลังบำบัด",
    "Bharani": "อดทน แบกรับ ผ่านการเกิดใหม่",
    "Krittika": "คมกริบ ตัดขาด เผาไหม้ กล้าแสดง",
    "Rohini": "งดงาม เจริญรุ่งเรือง มีเสน่ห์",
    "Mrigashira": "ช่างค้นหา กระตือรือร้น อ่อนโยน อยากรู้",
    "Ardra": "ผ่านพายุ เปลี่ยนแปลง ลึกซึ้ง คิดมาก",
    "Punarvasu": "ฟื้นคืน ใจกว้าง กลับมาเริ่มใหม่",
    "Pushya": "เลี้ยงดู อบอุ่น ศักดิ์สิทธิ์ มั่นคง",
    "Ashlesha": "ลึกลับ ฉลาด รู้เท่าทัน ผูกพันแรง",
    "Magha": "บรรพบุรุษ เกียรติ อำนาจ ภาคภูมิ",
    "Purva Phalguni": "รักสนุก ศิลปะ ความสุขทางใจ",
    "Uttara Phalguni": "เอื้อเฟื้อ มั่นคง มีความสุข พึ่งพาได้",
    "Hasta": "ฝีมือดี ชำนาญ ปราดเปรียว เจรจาเก่ง",
    "Chitra": "ประกายสร้างสรรค์ งดงาม ชอบออกแบบ",
    "Swati": "รักอิสระ ค้าขาย ต้องมีพื้นที่ของตัวเอง",
    "Vishakha": "มุ่งเป้า ชัยชนะ ไฟแรง ไม่ยอมหยุด",
    "Anuradha": "มิตรภาพ อดทน ศรัทธา ไปได้ไกล",
    "Jyeshtha": "อาวุโส มีอำนาจ ปกป้องพวกพ้อง",
    "Mula": "ถอนราก ค้นลึก ไปถึงต้นตอ เปลี่ยนชีวิต",
    "Purva Ashadha": "ไม่ยอมแพ้ ชักจูงเก่ง มั่นใจ",
    "Uttara Ashadha": "ชัยชนะถาวร คุณธรรม น่าเชื่อถือ",
    "Shravana": "ช่างฟัง เรียนรู้ ชื่อเสียงดี",
    "Dhanishta": "ทรัพย์และจังหวะ ดนตรี กลุ่มสังคม",
    "Shatabhisha": "นักรักษา เก็บความลับ ชอบสันโดษ",
    "Purva Bhadrapada": "อุดมการณ์แรง ไฟสูง เปลี่ยนแปลง",
    "Uttara Bhadrapada": "ลึก สงบ ปัญญา ผู้สนับสนุนเบื้องหลัง",
    "Revati": "เมตตา เป็นทางให้ผู้อื่น นำทาง",
}

LORD_TH = {
    "Ketu": "เกตุ", "Venus": "ศุกร์", "Sun": "อาทิตย์", "Moon": "จันทร์",
    "Mars": "อังคาร", "Rahu": "ราหู", "Jupiter": "พฤหัสบดี", "Saturn": "เสาร์",
    "Mercury": "พุธ",
}

TYPE_TH = {
    "Generator": "เครื่องกำเนิด (Generator)",
    "Manifesting Generator": "เครื่องกำเนิดที่ลงมือเอง (Manifesting Generator)",
    "Manifestor": "ผู้ประกาศ (Manifestor)",
    "Projector": "ผู้ชี้นำ (Projector)",
    "Reflector": "กระจกสะท้อน (Reflector)",
}

STRATEGY_TH = {
    "Wait to Respond": "รอการตอบสนองต่อสิ่งเร้า",
    "Wait to Respond, then Inform": "รอตอบสนอง แล้วบอกกล่าวก่อนลงมือ",
    "To Inform": "บอกกล่าวผู้อื่นก่อนลงมือ",
    "Wait for Recognition and the Invitation": "รอการยอมรับและการเชิญ",
    "Wait a Lunar Cycle (28 Days)": "รอหนึ่งรอบจันทรคติ (28 วัน)",
}

AUTHORITY_TH = {
    "Solar Plexus": "อารมณ์ — รอให้คลื่นอารมณ์นิ่งก่อนตัดสินใจ",
    "Sacral": "สัญชาตญาณท้อง — ตอบรับ/ปฏิเสธในปัจจุบันทันที",
    "Splenic": "ญาณหยั่งรู้ — สัญญาณเงียบ ๆ ครั้งเดียว เชื่อทันที",
    "Ego": "เจตจำนง — ตัดสินจากความต้องการที่แท้จริง",
    "Self Projected": "พูดออกมาเพื่อฟังทิศทางของตัวเอง",
    "Mental/Outer": "ปรึกษาผู้อื่นที่ไว้ใจ แล้วเชื่อในสภาพแวดล้อม",
    "Environmental": "รอรอบจันทรคติและลองสภาพแวดล้อม",
    "None": "ไม่มีศูนย์กลางอำนาจชัดเจน",
}

DEFINITION_TH = {
    "Single": "เดี่ยว — ประมวลผลในตัวครบถ้วน",
    "Split": "แยกสอง — ต้องหา 'อีกครึ่ง' มาเชื่อม (ธีมชีวิต)",
    "Triple Split": "แยกสาม — หลายส่วนที่ต้องประสานกัน",
    "Quadruple Split": "แยกสี่ — ซับซ้อน ต้องใช้เวลาเชื่อมโยง",
    "None": "ไม่มี (Reflector)",
}

PROFILE_TH = {
    "1/3": "นักสืบ/นักทดลอง — ต้องมีรากฐานแล้วลองผิดลองถูก",
    "1/4": "นักสืบ/นักเครือข่าย — สร้างฐานแล้วใช้อิทธิพลผ่านคนใกล้ตัว",
    "2/4": "นักบวช/นักเครือข่าย — พรสวรรค์ที่ถูกเรียกออกมา",
    "2/5": "นักบวช/ผู้แก้ปัญหา — พรสวรรค์ + ถูกคาดหวังให้แก้ปัญหา",
    "3/5": "นักทดลอง/ผู้แก้ปัญหา — เรียนรู้ด้วยการลอง ถูกมองเป็นผู้นำทาง",
    "3/6": "นักทดลอง/แบบอย่าง — ลองผิดลองถูกจนกลายเป็นต้นแบบ",
    "4/6": "นักเครือข่าย/แบบอย่าง — อิทธิพลสังคม + บทบาทแบบอย่าง",
    "4/1": "ผู้มีอิทธิพล/นักสืบ — โฟกัสแคบและลึก (Juxtaposition)",
    "5/1": "ผู้แก้ปัญหา/นักสืบ — นำด้วยวิธีปฏิบัติจากรากฐานที่แน่น",
    "5/2": "ผู้แก้ปัญหา/นักบวช — ถูกเรียกให้แก้ปัญหาโดยธรรมชาติ",
    "6/2": "แบบอย่าง/นักบวช — ชีวิตสามช่วง เห็นภาพกว้าง",
    "6/3": "แบบอย่าง/นักทดลอง — ผ่านประสบการณ์เพื่อเป็นต้นแบบ",
}

CENTER_TH = {
    "Head": "ศีรษะ", "Ajna": "อาณา", "Throat": "ลำคอ", "Self": "ตัวตน (G)",
    "Sacral": "ศักดิ์สิทธิ์ (Sacral)", "Root": "ราก", "Spleen": "ม้าม",
    "Solar Plexus": "สุริยะประสาท", "Heart": "หัวใจ (Ego)",
}


# ======================================================================
# 12 Life Stages (十二長生) + 神煞 stars
#   Formulas follow the classical (子平) tradition. Some schools differ on
#   a few stars — if a value disagrees with a reference calculator, adjust
#   the lookup tables below.
# ======================================================================

STAGE_INFO = [
    ("長生", "Birth (Chang Sheng)", "เกิด (เชียงแซ)"),
    ("沐浴", "Bath (Mu Yu)", "อาบน้ำ (บักยก)"),
    ("冠帶", "Youth (Guan Dai)", "สวมหมวก (กวงตั่ว)"),
    ("臨官", "Officer (Lin Guan)", "รับราชการ (ลิ่มกัว)"),
    ("帝旺", "Emperor (Di Wang)", "รุ่งโรจน์ (ตี่อ๋อง)"),
    ("衰", "Decay (Shuai)", "ถดถอย (ซวย)"),
    ("病", "Sick (Bing)", "เจ็บป่วย (แปะ)"),
    ("死", "Death (Si)", "ตาย (ซี้)"),
    ("墓", "Grave (Mu)", "สุสาน (หม่อ)"),
    ("絕", "Extinction (Jue)", "ดับสูญ (จุ๊ด)"),
    ("胎", "Fetus (Tai)", "ปฏิสนธิ (ไท)"),
    ("養", "Nourish (Yang)", "เลี้ยงดู (เอี้ยง)"),
]

# 長生 starting branch per day stem (0=甲 … 9=癸); yang forward, yin backward
_STAGE_START = {0: 11, 1: 6, 2: 2, 3: 9, 4: 2, 5: 9, 6: 5, 7: 0, 8: 8, 9: 3}

STAR_INFO = {
    "天乙貴人": ("Tian Yi Nobleman", "เทียนอี้กุ้ยเหริน (ดาวขุนนาง)"),
    "文昌": ("Intelligence Star", "เหวินชาง (ดาววิชาการ)"),
    "太極貴人": ("Tai Ji Nobleman", "ไท่จี๋กุ้ยเหริน"),
    "桃花": ("Peach Blossom Star", "ท้อฮวย (ดาวเสน่ห์)"),
    "驛馬": ("Sky Horse / Travelling Horse", "ดาวม้า (ดาวเดินทาง)"),
    "將星": ("General Star", "เจียงซิง (ดาวแม่ทัพ)"),
    "孤辰": ("Solitary Star", "กูเฉิน (ดาวโดดเดี่ยวชาย)"),
    "寡宿": ("Lonesome Star", "กวาสู้ (ดาวว้าเหว่หญิง)"),
    "紅艷煞": ("Red Blossom Star", "มารเสน่ห์แดง (ดาวเสน่ห์ลุ่มหลง)"),
    "天德貴人": ("Heavenly Virtue Star", "เทียนเต๋อกุ้ยเหริน (ดาวคุณธรรมสวรรค์)"),
    "月德貴人": ("Monthly Virtue Star", "เย่วเต๋อกุ้ยเหริน (ดาวคุณธรรมจันทรา)"),
    "羊刃": ("Goat Blade / Sword Star", "ดาวดาบ (ดาวแกะ)"),
    "干祿": ("Prosperity Star (Gan Lu)", "ดาวโชคลาภหลัก"),
    "福星貴人": ("Fu Star Nobleman", "ฮกแชกุ้ยนั้ง (ดาวอุปถัมภ์โชคลาภ)"),
    "華蓋": ("Talent / Elegant Canopy Star", "ดาวฮั่วไก่ (ดาวศิลปะสันโดษ)"),
    "劫煞": ("Robbery Sha", "เจี๋ยซา (ดาวปล้นสะดม)"),
    "亡神": ("Death God Star", "หวังเสิน (ดาวสูญเสีย)"),
    "災煞": ("Calamity Sha", "จั้ยซา (ดาวเคราะห์กรรม)"),
}

STAR_MEANING = {
    "天乙貴人": "มีผู้ใหญ่/ผู้มีบุญคุณคอยช่วยเหลือ ยามตกยากมีทางออก",
    "文昌": "ปัญญาดี การเรียนและงานวิชาการเด่น เหมาะงานที่ใช้ความรู้",
    "太極貴人": "ใจนักปราชญ์ สนใจศาสตร์ลึก เชื่อมโยงสิ่งต่าง ๆ ได้ดี",
    "桃花": "เสน่ห์ด้านความรัก มีคนนิยมชมชอบ ระวังเรื่องชู้สาว",
    "驛馬": "ชีวิตเคลื่อนไหว เดินทาง/ย้ายถิ่นบ่อย โอกาสมักมาจากที่ไกล",
    "將星": "ภาวะผู้นำ อำนาจบารมี เหมาะเป็นหัวหน้าหรือผู้ควบคุม",
    "孤辰": "ชอบอยู่คนเดียว ใจแข็ง ต้องระวังความเหงา",
    "寡宿": "ต้องการพื้นที่ส่วนตัว อาจรู้สึกว้าเหว่ในบางช่วง",
    "紅艷煞": "เสน่ห์รุนแรง น่าดึงดูด ระวังความลุ่มหลง",
    "天德貴人": "มีคุณธรรม คิดดีทำดี มีสิ่งศักดิ์สิทธิ์คุ้มครอง",
    "月德貴人": "มีเมตตา เป็นที่รักของผู้คน มักได้รับความช่วยเหลือ",
    "羊刃": "ใจเด็ด กล้าได้กล้าเสีย พลังแรง เหมาะงานท้าทาย",
    "干祿": "มีเกณฑ์ได้ทรัพย์จากการทำงาน มีข้าวมีของ",
    "福星貴人": "โชคลาภและความสุข ไม่ลำบากเกินไป มีคนอุปถัมภ์",
    "華蓋": "ศิลปะ/ศาสนา/สันโดษ มีมุมคิดลึกที่ไม่เหมือนใคร",
    "劫煞": "ระวังการเสียทรัพย์หรือถูกแย่งชิง แต่มีพลังดิ้นรน",
    "亡神": "ใจลอย ต้องระวังการสูญเสียและสุขภาพจิต",
    "災煞": "มีเกณฑ์เคราะห์/อุบัติเหตุ ควรระวังและทำบุญ",
}

_TIANYI = {0: [1, 7], 4: [1, 7], 6: [1, 7], 1: [0, 8], 5: [0, 8],
           2: [11, 9], 3: [11, 9], 7: [6, 2], 8: [3, 5], 9: [3, 5]}
_WENCHANG = [5, 6, 8, 9, 8, 9, 11, 0, 2, 3]
_TAIJI = {0: [0, 6], 1: [0, 6], 2: [3, 9], 3: [3, 9], 4: [4, 10, 1, 7],
          5: [4, 10, 1, 7], 6: [2, 11], 7: [2, 11], 8: [5, 8], 9: [5, 8]}
_HONGYAN = [6, 6, 2, 7, 4, 4, 10, 9, 0, 8]
_YANGREN = [3, 4, 6, 7, 6, 7, 9, 10, 0, 1]
_GANLU = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0]
_FUXING = [2, 1, 0, 9, 8, 7, 6, 5, 4, 3]
_TAOHUA = {"szc": 9, "ywx": 3, "syc": 6, "hmw": 0}
_YIMA = {"szc": 2, "ywx": 8, "syc": 11, "hmw": 5}
_JIANGXING = {"szc": 0, "ywx": 6, "syc": 9, "hmw": 3}
_HUAGAI = {"szc": 4, "ywx": 10, "syc": 1, "hmw": 7}
_JIESHA = {"szc": 5, "ywx": 11, "syc": 2, "hmw": 8}
_WANGSHEN = {"szc": 11, "ywx": 5, "syc": 8, "hmw": 2}
_ZAISHA = {"szc": 6, "ywx": 0, "syc": 3, "hmw": 9}
_GUCHEN = [2, 5, 8, 11]
_GUASU = [10, 1, 4, 7]
_TIANDE = {2: ("s", 3), 3: ("b", 8), 4: ("s", 8), 5: ("s", 7), 6: ("b", 11),
           7: ("s", 0), 8: ("s", 9), 9: ("b", 2), 10: ("s", 2), 11: ("s", 1),
           0: ("b", 5), 1: ("s", 6)}
_YUEDE = {2: 2, 6: 2, 10: 2, 8: 8, 0: 8, 4: 8, 11: 0, 3: 0, 7: 0, 5: 6, 9: 6, 1: 6}


def _life_stage(day_stem: int, branch: int) -> int:
    start = _STAGE_START[day_stem]
    if day_stem % 2 == 0:
        return (branch - start) % 12
    return (start - branch) % 12


def _triad(b: int) -> str:
    if b in (8, 0, 4):
        return "szc"
    if b in (2, 6, 10):
        return "ywx"
    if b in (5, 9, 1):
        return "syc"
    return "hmw"


def _quadrant(b: int) -> int:
    if b in (11, 0, 1):
        return 0
    if b in (2, 3, 4):
        return 1
    if b in (5, 6, 7):
        return 2
    return 3


def _shen_sha(fp: dict) -> dict:
    ys = fp["year"]["stem"]["index"]
    ds = fp["day"]["stem"]["index"]
    yb = fp["year"]["branch"]["index"]
    mb = fp["month"]["branch"]["index"]
    db = fp["day"]["branch"]["index"]
    stems = {"year": ys, "month": fp["month"]["stem"]["index"],
             "day": ds, "hour": fp["hour"]["stem"]["index"]}
    branches = {"year": yb, "month": mb, "day": db,
                "hour": fp["hour"]["branch"]["index"]}
    out: dict = {}

    def add(star: str, pillar: str) -> None:
        out.setdefault(star, []).append(pillar)

    def match(star: str, targets) -> None:
        for p, b in branches.items():
            if b in targets:
                add(star, p)

    for star, table in (("天乙貴人", _TIANYI), ("太極貴人", _TAIJI)):
        match(star, set(table[ds]) | set(table[ys]))
    match("文昌", {_WENCHANG[ds], _WENCHANG[ys]})
    match("福星貴人", {_FUXING[ds], _FUXING[ys]})
    match("紅艷煞", {_HONGYAN[ds]})
    match("羊刃", {_YANGREN[ds]})
    match("干祿", {_GANLU[ds]})
    for star, table in (("桃花", _TAOHUA), ("驛馬", _YIMA), ("將星", _JIANGXING),
                        ("華蓋", _HUAGAI), ("劫煞", _JIESHA),
                        ("亡神", _WANGSHEN), ("災煞", _ZAISHA)):
        match(star, {table[_triad(yb)], table[_triad(db)]})
    match("孤辰", {_GUCHEN[_quadrant(yb)]})
    match("寡宿", {_GUASU[_quadrant(yb)]})

    tde = _TIANDE[mb]
    if tde[0] == "s":
        for p, s in stems.items():
            if s == tde[1]:
                add("天德貴人", p)
    else:
        match("天德貴人", {tde[1]})
    yde = _YUEDE[mb]
    for p, s in stems.items():
        if s == yde:
            add("月德貴人", p)

    return out


# ----------------------------------------------------------------------
# Na Yin (納音), Kong Wang (空亡), Da Yun (大運)
# ----------------------------------------------------------------------

NAYIN = [
    ("海中金", "ทองในทะเล"), ("爐中火", "ไฟในเตา"), ("大林木", "ไม้ใหญ่ในป่า"),
    ("路旁土", "ดินข้างทาง"), ("劍鋒金", "ทองปลายดาบ"), ("山頭火", "ไฟบนยอดเขา"),
    ("澗下水", "น้ำใต้ธาร"), ("城頭土", "ดินบนกำแพงเมือง"), ("白蠟金", "ทองขี้ผึ้งขาว"),
    ("楊柳木", "ไม้หลิว"), ("泉中水", "น้ำในตาน้ำ"), ("屋上土", "ดินบนหลังคา"),
    ("霹靂火", "ไฟฟ้าผ่า"), ("松柏木", "ไม้สน"), ("長流水", "น้ำไหลไม่หยุด"),
    ("沙中金", "ทองในทราย"), ("山下火", "ไฟเชิงเขา"), ("平地木", "ไม้บนที่ราบ"),
    ("壁上土", "ดินบนกำแพง"), ("金箔金", "ทองแผ่นบาง"), ("覆燈火", "ไฟใต้โคม"),
    ("天河水", "น้ำทางช้างเผือก"), ("大驛土", "ดินริมทางใหญ่"), ("釵釧金", "ทองเครื่องประดับ"),
    ("桑柘木", "ไม้หม่อน"), ("大溪水", "น้ำลำธารใหญ่"), ("沙中土", "ดินในทราย"),
    ("天上火", "ไฟบนสวรรค์"), ("石榴木", "ไม้ทับทิม"), ("大海水", "น้ำมหาสมุทร"),
]


def _jiazi_index(stem: int, branch: int) -> int:
    for n in range(60):
        if n % 10 == stem and n % 12 == branch:
            return n
    return 0


def _nayin(stem: int, branch: int):
    return NAYIN[_jiazi_index(stem, branch) // 2]


def _kongwang(stem: int, branch: int):
    head = (branch - stem) % 12
    return (head + 10) % 12, (head + 11) % 12


def _da_yun(fp: dict, jd: float, gender: str):
    """Return (forward, start_age, cycles) using the classical 3-day=1-year rule."""
    y_stem = fp["year"]["stem"]["index"]
    m_stem = fp["month"]["stem"]["index"]
    m_branch = fp["month"]["branch"]["index"]
    yang_year = y_stem % 2 == 0
    forward = (yang_year and gender == "male") or (not yang_year and gender == "female")

    year = int(swe.revjul(jd)[0])
    terms = []
    for yy in (year - 1, year, year + 1):
        for lon in BaZiEngine._MAJOR_LONS:
            terms.append(BaZiEngine._find_major_term(yy, lon))
    terms.sort()
    if forward:
        boundary = min(t for t in terms if t > jd)
    else:
        boundary = max(t for t in terms if t < jd)
    start_age = abs(boundary - jd) / 3.0

    base = _jiazi_index(m_stem, m_branch)
    step = 1 if forward else -1
    cycles = []
    for i in range(1, 11):
        idx = (base + step * i) % 60
        cycles.append((round(start_age + (i - 1) * 10, 1), idx % 10, idx % 12))
    return forward, start_age, cycles


# ----------------------------------------------------------------------
# Strength / favourable elements / yearly pillars
# ----------------------------------------------------------------------

_ELEMENT_GROUPS = ["Wood", "Fire", "Earth", "Metal", "Water"]
_ELEMENT_GROUP_TH = {"Wood": "ไม้", "Fire": "ไฟ", "Earth": "ดิน", "Metal": "ทอง", "Water": "น้ำ"}


def _strength(five_elements: dict, dm_index: int):
    """Rough day-master strength and favourable/unfavourable elements."""
    g = dm_index // 2
    support = (_ELEMENT_GROUPS[g], _ELEMENT_GROUPS[(g + 4) % 5])
    drain = (_ELEMENT_GROUPS[(g + 1) % 5], _ELEMENT_GROUPS[(g + 2) % 5],
             _ELEMENT_GROUPS[(g + 3) % 5])
    sup = sum(five_elements.get(e, 0) for e in support)
    total = sum(five_elements.values()) or 1
    ratio = sup / total
    strong = ratio >= 0.5
    favorable = list(drain) if strong else list(support)
    unfavorable = list(support) if strong else list(drain)
    return ratio, strong, favorable, unfavorable


def _year_pillar(year: int):
    return (year - 4) % 10, (year - 4) % 12


# ======================================================================
# Ten deities — computed correctly here (direct/indirect by polarity)
# ======================================================================

def _ten_deity(day_idx: int, other_idx: int) -> str:
    """Return the ten-deity label for *other_idx* relative to *day_idx*."""
    dg, og = day_idx // 2, other_idx // 2
    same_pol = (day_idx % 2) == (other_idx % 2)
    if og == dg:
        return "比肩" if same_pol else "劫财"
    if og == (dg + 1) % 5:
        return "食神" if same_pol else "伤官"
    if og == (dg + 2) % 5:
        return "偏财" if same_pol else "正财"
    if og == (dg + 3) % 5:
        return "七杀" if same_pol else "正官"
    return "偏印" if same_pol else "正印"


# ======================================================================
# Section renderers
# ======================================================================

def render_bazi(b: dict, jd: float | None = None, gender: str | None = None) -> str:
    lines = ["☯" * 22 + " 1. ปาจื่อ / สี่เสา (BaZi) " + "☯" * 22]

    dm = b["day_master"]
    elem = dm["element"]
    polarity = "yang" if dm["index"] % 2 == 0 else "yin"
    lines.append("")
    lines.append(f"ธาตุเจ้าชะตา (Day Master): {STEM_TH.get(dm['pinyin'], dm['pinyin'])} "
                 f"({dm['cn']}) ธาตุ{ELEMENT_TH[elem]}")
    lines.append(f"  นิสัย: {DAY_MASTER_TH[elem]}")
    lines.append(f"  ขั้ว: {POLARITY_TH[polarity]}")
    lines.append(f"  เวลาสุริยะจริง (True Solar Time): {b['true_solar_time']} น. "
                 f"| เทอมสุริยะ: {b['solar_term_name']}")

    lines.append("")
    lines.append("— สี่เสา (Four Pillars) —")
    fp = b["four_pillars"]
    for key in ("year", "month", "day", "hour"):
        p = fp[key]
        stem = p["stem"]
        branch = p["branch"]
        hidden = ", ".join(
            f"{STEM_TH.get(h['pinyin'], h['pinyin'])}{h['cn']}({ELEMENT_TH[h['element']]})"
            for h in p["hidden_stems"]
        )
        lines.append(f"  [{key.upper()}] {PILLAR_TH[key]}")
        lines.append(f"        ก้านฟ้า: {STEM_TH.get(stem['pinyin'], stem['pinyin'])}{stem['cn']} "
                     f"({ELEMENT_TH[stem['element']]}) | "
                     f"ก้านดิน: {branch['pinyin']}{branch['cn']} ({ELEMENT_TH[branch['element']]})")
        ny_zh, ny_th = _nayin(stem["index"], branch["index"])
        lines.append(f"        纳音 (Na Yin): {ny_zh} — {ny_th}")
        if hidden:
            lines.append(f"        ธาตุแฝง: {hidden}")

    lines.append("")
    lines.append("— เทพสิบ (Ten Deities) —")
    day_idx = fp["day"]["stem"]["index"]
    for key in ("year", "month", "day", "hour"):
        s = fp[key]["stem"]
        if key == "day":
            head = "日主 (เจ้าชะตา / Day Master) [DM]"
        else:
            head = _fmt_deity(_ten_deity(day_idx, s["index"]))
        lines.append(f"  [{key.upper()}] ก้านฟ้า {STEM_TH.get(s['pinyin'], s['pinyin'])}{s['cn']}"
                     f" ({ELEMENT_TH[s['element']]}): {head}")
        hidden = fp[key]["hidden_stems"]
        if hidden:
            parts = []
            for hs in hidden:
                d = _ten_deity(day_idx, hs["index"])
                parts.append(f"{STEM_TH.get(hs['pinyin'], hs['pinyin'])}{hs['cn']}={DEITY_CODE.get(d, '?')}")
            lines.append(f"        ก้านดิน (ธาตุแฝง): {', '.join(parts)}")

    lines.append("")
    lines.append("— ระยะสิบสอง (十二長生 / Pillar Phase) —")
    for key in ("year", "month", "day", "hour"):
        br = fp[key]["branch"]["index"]
        zh, en, th = STAGE_INFO[_life_stage(day_idx, br)]
        lines.append(f"  [{key.upper()}] {zh} {en} — {th}")

    lines.append("")
    lines.append("— ดาวมงคล/กาลกิณี (神煞) —")
    stars = _shen_sha(fp)
    if not stars:
        lines.append("  ไม่พบดาว神煞ในดวงนี้")
    else:
        for star, (en, th) in STAR_INFO.items():
            if star not in stars:
                continue
            marks = "".join(
                f"({'YMDH'[i]})" for i, p in enumerate(("year", "month", "day", "hour"))
                if p in stars[star]
            )
            lines.append(f"  {star} {en} — {th}  {marks}")

    lines.append("")
    lines.append("— สมดุลห้าธาตุ —")
    fe = b["five_elements"]
    for e, c in fe.items():
        bar = "█" * max(1, int(round(c))) if c > 0 else "·"
        lines.append(f"  {ELEMENT_TH[e]:<4} {c:>4}  {bar}")
    dominant = max(fe, key=fe.get)
    missing = [e for e, c in fe.items() if c == 0]
    lines.append(f"  ธาตุเด่น: {ELEMENT_TH[dominant]}")
    if missing:
        lines.append(f"  ธาตุขาด: {', '.join(ELEMENT_TH[e] for e in missing)}")
        for e in missing:
            lines.append(f"    → {ELEMENT_ADVICE_TH[e]}")
    else:
        lines.append("  ธาตุครบทั้งห้า — สมดุลดี")

    ratio, strong, favorable, unfavorable = _strength(fe, day_idx)
    lines.append("")
    lines.append("— กำลังเจ้าชะตา (Day Master Strength) —")
    lines.append(f"  คะแนนสนับสนุน: {ratio * 100:.0f}% → "
                 f"{'แข็ง (身強) ต้องระบาย/ควบคุม' if strong else 'อ่อน (身弱) ต้องเสริม/หนุน'}")
    lines.append(f"  ธาตุที่ควรเสริม (喜用神): {', '.join(_ELEMENT_GROUP_TH[e] for e in favorable)}")
    lines.append(f"  ธาตุที่ควรเลี่ยง (忌神): {', '.join(_ELEMENT_GROUP_TH[e] for e in unfavorable)}")

    lines.append("")
    lines.append("— 空亡 (Kong Wang / ธาตุว่าง) —")
    for key in ("day", "year"):
        s = fp[key]["stem"]["index"]
        br = fp[key]["branch"]["index"]
        k1, k2 = _kongwang(s, br)
        lines.append(f"  [{key.upper()}] {EARTHLY_BRANCHES[k1][1]} {EARTHLY_BRANCHES[k2][1]} "
                     f"({EARTHLY_BRANCHES[k1][0]}, {EARTHLY_BRANCHES[k2][0]})")

    def _pillar_label(s: int, br: int) -> str:
        return (f"{STEM_TH.get(HEAVENLY_STEMS[s][0], HEAVENLY_STEMS[s][0])}{HEAVENLY_STEMS[s][1]}"
                f"{EARTHLY_BRANCHES[br][0]}{EARTHLY_BRANCHES[br][1]}")

    if jd is not None and gender in ("male", "female"):
        forward, start_age, cycles = _da_yun(fp, jd, gender)
        lines.append("")
        lines.append(f"— 大運 (Da Yun / วงจร 10 ปี) — "
                     f"{'เดินหน้า' if forward else 'ถอยหลัง'} เริ่มราวอายุ {start_age:.1f} ปี —")
        for age, s, br in cycles:
            deity = _ten_deity(day_idx, s)
            code = DEITY_CODE.get(deity, "?")
            zh, _, th = STAGE_INFO[_life_stage(day_idx, br)]
            mark = " ★ธาตุมงคล" if HEAVENLY_STEMS[s][2] in favorable else ""
            lines.append(
                f"  อายุ {age:>5.1f}: {_pillar_label(s, br)} "
                f"({ELEMENT_TH[HEAVENLY_STEMS[s][2]]}/{ELEMENT_TH[EARTHLY_BRANCHES[br][2]]}) "
                f"— {zh} {th} | {code}{mark}"
            )
    elif jd is not None:
        lines.append("")
        lines.append("— 大運 (Da Yun) — ต้องระบุเพศ (gender) เพื่อคำนวณทิศทาง")

    birth_year = int(swe.revjul(jd)[0]) if jd is not None else None
    if birth_year is not None:
        start_year = datetime.now().year
        lines.append("")
        lines.append(f"— 流年 (Liu Nian / รายปี) — {start_year}–{start_year + 9} —")
        for yr in range(start_year, start_year + 10):
            s, br = _year_pillar(yr)
            deity = _ten_deity(day_idx, s)
            code = DEITY_CODE.get(deity, "?")
            mark = " ★" if HEAVENLY_STEMS[s][2] in favorable else ""
            lines.append(
                f"  {yr} (อายุ {yr - birth_year:>2}): {_pillar_label(s, br)} "
                f"({ELEMENT_TH[HEAVENLY_STEMS[s][2]]}/{ELEMENT_TH[EARTHLY_BRANCHES[br][2]]}) "
                f"| {code}{mark}"
            )

    return "\n".join(lines)


def render_western(w: dict) -> str:
    lines = ["☸" * 22 + " 2. โหราศาสตร์ตะวันตก (Western) " + "☸" * 22]

    ac = w["ascendant"]
    mc = w["midheaven"]
    lines.append("")
    lines.append(f"ลัคนา (Ascendant): ราศี{SIGN_TH[_sign_name(ac)]} {ac % 30:.2f}° "
                 "— บุคลิกที่คนอื่นเห็น")
    lines.append(f"จุดกลางฟ้า (MC): ราศี{SIGN_TH[_sign_name(mc)]} {mc % 30:.2f}° "
                 "— อาชีพและทิศทางชีวิต")

    lines.append("")
    lines.append("— ดาวเคราะห์ —")
    houses = w["houses"]

    def house_of(deg: float) -> int:
        for i in range(12):
            a = houses[i]
            b = houses[(i + 1) % 12]
            span = (b - a) % 360
            if (deg - a) % 360 < span:
                return i + 1
        return 12

    for planet, info in w["planets"].items():
        name_th, meaning = PLANET_TH.get(planet, (planet, ""))
        h = house_of(info["degree"])
        lines.append(f"  {name_th:<12} ราศี{SIGN_TH[info['sign']]:<7} {info['sign_degree']:>6.2f}° "
                     f"| เรือน {h} ({HOUSE_TH[h - 1]})")
        if planet in ("Sun", "Moon"):
            lines.append(f"               → {meaning}")

    lines.append("")
    lines.append("— มุมสัมพันธ์ (Aspects) —")
    if not w["aspects"]:
        lines.append("  ไม่พบมุมสัมพันธ์ในช่วงออร์บที่กำหนด")
    for asp in sorted(w["aspects"], key=lambda a: a["orb"])[:12]:
        p1 = PLANET_TH.get(asp["planet1"], (asp["planet1"],))[0]
        p2 = PLANET_TH.get(asp["planet2"], (asp["planet2"],))[0]
        nature = ASPECT_TH.get(asp["aspect"], asp["aspect"])
        lines.append(f"  {p1:<10} {nature:<8} {p2:<10} "
                     f"(มุม {asp['angle']}°, ออร์บ {asp['orb']}°)")

    return "\n".join(lines)


def render_vedic(v: dict) -> str:
    lines = ["🕉" * 22 + " 3. โหราศาสตร์ภารตะ (Vedic) " + "🕉" * 22]
    lines.append("")

    moon = v["planets"].get("Moon")
    sun = v["planets"].get("Sun")
    if moon:
        lines.append("— จิตใจและอารมณ์ (จากดวงจันทร์) —")
        lines.append(f"  ราศีจันทร์ (Janma Rashi): ราศี{RASHI_TH.get(moon['rashi'], moon['rashi'])}")
        lines.append(f"  นักษัตร: {moon['nakshatra']} (บาทที่ {moon['pada']}) "
                     f"| เจ้าเรือน: {LORD_TH.get(moon['nakshatra_lord'], moon['nakshatra_lord'])}")
        lines.append(f"  ลักษณะ: {NAKSHATRA_TH.get(moon['nakshatra'], '')}")
        lines.append(f"  นวางศ์ (D9): ราศี{RASHI_TH.get(moon['navamsha_rashi'], moon['navamsha_rashi'])}")
    if sun:
        lines.append("")
        lines.append(f"— จุดมุ่งหมาย (จากดวงอาทิตย์) —")
        lines.append(f"  ราศีอาทิตย์: ราศี{RASHI_TH.get(sun['rashi'], sun['rashi'])} "
                     f"| นักษัตร: {sun['nakshatra']} (บาทที่ {sun['pada']})")

    lines.append("")
    lines.append("— ตำแหน่งดาวนิรายนะ (Sidereal) —")
    for planet, info in v["planets"].items():
        name_th = PLANET_TH.get(planet, (planet,))[0]
        lines.append(f"  {name_th:<12} ราศี{RASHI_TH.get(info['rashi'], info['rashi']):<7} "
                     f"| {info['nakshatra']} บาท {info['pada']}")

    return "\n".join(lines)


def render_hd(h: dict) -> str:
    lines = ["✦" * 22 + " 4. ฮิวแมนดีไซน์ (Human Design) " + "✦" * 22]
    lines.append("")
    lines.append(f"ประเภท (Type): {TYPE_TH.get(h['type'], h['type'])}")
    lines.append(f"  กลยุทธ์: {STRATEGY_TH.get(h['strategy'], h['strategy'])}")
    lines.append(f"  สัญญาณบวก: {h['signature']} | สัญญาณลบ: {h['not_self_theme']}")
    lines.append("")
    lines.append(f"อำนาจตัดสินใจ (Authority): {AUTHORITY_TH.get(h['authority'], h['authority'])}")
    lines.append(f"โครงสร้าง (Definition): {DEFINITION_TH.get(h['definition'], h['definition'])}")
    lines.append(f"โปรไฟล์: {h['profile']} — {PROFILE_TH.get(h['profile'], '')}")
    lines.append(f"ไม้กางเขนชาติกำเนิด: {h['incarnation_cross']}")
    lines.append(f"Variable: {h['variable']}")
    lines.append("")
    lines.append("— ศูนย์พลังงาน (Centers) —")
    lines.append(f"  กำหนดชัด (Defined): {', '.join(CENTER_TH.get(c, c) for c in h['defined_centers']) or '—'}")
    lines.append(f"  เปิดรับ (Undefined): {', '.join(CENTER_TH.get(c, c) for c in h['undefined_centers']) or '—'}")
    if h["active_channels"]:
        chans = ", ".join(f"{a}-{b}" for a, b in h["active_channels"])
        lines.append(f"  ช่องทางที่เปิด (Channels): {chans}")
    lines.append(f"  ประตูที่เปิด (Gates): {', '.join(str(g) for g in h['all_active_gates'])}")
    return "\n".join(lines)


def render_summary(b: dict, w: dict, v: dict, h: dict) -> str:
    lines = ["✧" * 22 + " 5. คำอ่านสรุป (Reading) " + "✧" * 22]
    fp = b["four_pillars"]
    dm = b["day_master"]
    elem = dm["element"]
    day_idx = fp["day"]["stem"]["index"]
    ratio, strong, favorable, unfavorable = _strength(b["five_elements"], day_idx)

    lines.append("")
    lines.append(f"เจ้าชะตาธาตุ{ELEMENT_TH[elem]} ({dm['cn']}) — {DAY_MASTER_TH[elem]}")
    lines.append(
        f"กำลังธาตุ{'แข็ง' if strong else 'อ่อน'} ({ratio * 100:.0f}%): "
        + ("ใช้พลังสร้างผลงานแล้วปล่อยออก ไม่ควรเก็บกด"
           if strong else "ควรหาที่พึ่งและคนหนุน อย่าแบกทุกอย่างคนเดียว")
    )

    counts: dict = {}
    for key in ("year", "month", "hour"):
        counts[_ten_deity(day_idx, fp[key]["stem"]["index"])] = \
            counts.get(_ten_deity(day_idx, fp[key]["stem"]["index"]), 0) + 1
    if counts:
        lines.append("")
        lines.append("ธีมชีวิตจากเทพสิบ:")
        for d, n in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {DEITY_TH.get(d, d)}" + (f" (x{n})" if n > 1 else ""))

    stars = _shen_sha(fp)
    if stars:
        lines.append("")
        lines.append("ดาวที่ควรรู้ (神煞):")
        for star in STAR_INFO:
            if star in stars and star in STAR_MEANING:
                marks = "".join(
                    f"({'YMDH'[i]})" for i, p in enumerate(("year", "month", "day", "hour"))
                    if p in stars[star]
                )
                lines.append(f"  • {star} {marks}: {STAR_MEANING[star]}")

    lines.append("")
    lines.append("จากฮิวแมนดีไซน์:")
    lines.append(f"  • เป็น {TYPE_TH.get(h['type'], h['type'])} → {STRATEGY_TH.get(h['strategy'], h['strategy'])}")
    lines.append(f"  • ตัดสินใจด้วย {AUTHORITY_TH.get(h['authority'], h['authority'])}")
    lines.append(f"  • โปรไฟล์ {h['profile']}: {PROFILE_TH.get(h['profile'], '')}")

    sun = w["planets"].get("Sun")
    moon = w["planets"].get("Moon")
    lines.append("")
    lines.append("จากโหราศาสตร์ตะวันตก:")
    if sun:
        lines.append(f"  • อาทิตย์ราศี{SIGN_TH[sun['sign']]} — แก่นตัวตนและจุดมุ่งหมาย")
    if moon:
        lines.append(f"  • จันทร์ราศี{SIGN_TH[moon['sign']]} — โลกอารมณ์และความต้องการในใจ")
    lines.append(f"  • ลัคนาราศี{SIGN_TH[_sign_name(w['ascendant'])]} — ภาพที่คนอื่นเห็น")

    lines.append("")
    lines.append(
        f"ข้อเสนอ: เสริมธาตุ{', '.join(_ELEMENT_GROUP_TH[e] for e in favorable)}"
        f" (สี/อาชีพ/กิจกรรม/คนรอบข้าง) และลดการพึ่งธาตุ"
        f"{', '.join(_ELEMENT_GROUP_TH[e] for e in unfavorable)}"
    )
    return "\n".join(lines)


def _sign_name(deg: float) -> str:
    idx = int((deg % 360) // 30)
    return [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ][idx]


# ======================================================================
# Orchestration
# ======================================================================

def build_reading(data: dict) -> str:
    swe.set_ephe_path(default_ephe_path())

    hour_ut = data["hour"] + data["minute"] / 60.0 - data["tz_offset"]
    jd = swe.julday(data["year"], data["month"], data["day"], hour_ut)

    bazi = BaZiEngine.calculate(jd, data["lat"], data["lon"], data["tz_offset"])
    western = WesternEngine.calculate(jd, data["lat"], data["lon"])
    vedic = VedicEngine.calculate(jd)
    hd = HDEngine.calculate(jd)

    header = (
        "=" * 66 + "\n"
        f" คำอ่านดวงชะตา — {data['year']}-{data['month']:02d}-{data['day']:02d} "
        f"{data['hour']:02d}:{data['minute']:02d} "
        f"(UTC{data['tz_offset']:+.1f})\n"
        f" พิกัด {data['lat']}, {data['lon']}\n"
        + "=" * 66
    )

    return "\n\n".join([
        header,
        render_bazi(bazi, jd, data.get("gender")),
        render_western(western),
        render_vedic(vedic),
        render_hd(hd),
        render_summary(bazi, western, vedic, hd),
        "=" * 66,
    ])


DEFAULT_INPUT = {
    "year": 1992, "month": 8, "day": 8, "hour": 16, "minute": 49,
    "lat": 6.53995, "lon": 101.29, "tz_offset": 7,
}


def _usage() -> None:
    print(
        "Usage: python reading.py [year month day hour minute lat lon tz_offset [gender]]\n"
        "   gender: m/f (male/female) — optional, needed for 大運 (Da Yun)\n"
        "   or: WOR_INPUT='{\"year\":...,\"month\":...,\"day\":...,\"hour\":...,"
        "\"minute\":...,\"lat\":...,\"lon\":...,\"tz_offset\":...,\"gender\":\"male\"}' python reading.py",
        file=sys.stderr,
    )


def _norm_gender(value) -> str | None:
    if not value:
        return None
    v = str(value).strip().lower()
    if v in ("m", "male", "man", "ชาย"):
        return "male"
    if v in ("f", "female", "woman", "หญิง"):
        return "female"
    return None


def _parse_input() -> dict:
    env = os.environ.get("WOR_INPUT")
    if env:
        try:
            data = json.loads(env)
        except json.JSONDecodeError as exc:
            print(f"Error: WOR_INPUT is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(1)
        data["gender"] = _norm_gender(data.get("gender"))
        return data
    args = sys.argv[1:]
    if not args:
        return DEFAULT_INPUT
    if len(args) not in (8, 9):
        _usage()
        sys.exit(1)
    try:
        data = {
            "year": int(args[0]), "month": int(args[1]), "day": int(args[2]),
            "hour": int(args[3]), "minute": int(args[4]),
            "lat": float(args[5]), "lon": float(args[6]), "tz_offset": float(args[7]),
        }
        if len(args) == 9:
            data["gender"] = _norm_gender(args[8])
        return data
    except ValueError:
        _usage()
        sys.exit(1)


if __name__ == "__main__":
    print(build_reading(_parse_input()))
