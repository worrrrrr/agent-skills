"""Full-spectrum astronomical engine — BaZi, Western, Vedic, Human Design.

Uses Swiss Ephemeris (pyswisseph) for all planetary calculations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Swiss Ephemeris
# ---------------------------------------------------------------------------

_HAS_SWE = False
try:
    import swisseph as swe

    _HAS_SWE = True
except ImportError:
    pass

# ======================================================================
# BaZi constants
# ======================================================================

HEAVENLY_STEMS = [
    ("Jia", "甲", "Wood"),
    ("Yi", "乙", "Wood"),
    ("Bing", "丙", "Fire"),
    ("Ding", "丁", "Fire"),
    ("Wu", "戊", "Earth"),
    ("Ji", "己", "Earth"),
    ("Geng", "庚", "Metal"),
    ("Xin", "辛", "Metal"),
    ("Ren", "壬", "Water"),
    ("Gui", "癸", "Water"),
]

EARTHLY_BRANCHES = [
    ("Zi", "子", "Water"),
    ("Chou", "丑", "Earth"),
    ("Yin", "寅", "Wood"),
    ("Mao", "卯", "Wood"),
    ("Chen", "辰", "Earth"),
    ("Si", "巳", "Fire"),
    ("Wu", "午", "Fire"),
    ("Wei", "未", "Earth"),
    ("Shen", "申", "Metal"),
    ("You", "酉", "Metal"),
    ("Xu", "戌", "Earth"),
    ("Hai", "亥", "Water"),
]

# Hidden Stems (藏干) per branch
HIDDEN_STEMS: Dict[int, List[int]] = {
    0: [0, 9, 7],   # Zi (鼠): 癸, 辛, 壬
    1: [5, 3, 1],   # Chou (牛): 己, 丁, 乙
    2: [2, 0, 4],   # Yin (虎): 丙, 甲, 戊
    3: [1],          # Mao (兔): 乙
    4: [4, 1, 9],   # Chen (龙): 戊, 乙, 癸
    5: [6, 4, 2],   # Si (蛇): 庚, 戊, 丙
    6: [8, 3, 5],   # Wu (马): 壬, 丁, 己
    7: [5, 9, 3],   # Wei (羊): 己, 癸, 丁
    8: [6, 4, 8],   # Shen (猴): 庚, 戊, 壬
    9: [7],          # You (鸡): 辛
    10: [4, 7, 3],  # Xu (狗): 戊, 辛, 丁
    11: [2, 8],     # Hai (猪): 丙, 壬
}

# Ten Deities table: DayMaster element → Other element → Deity
# Wood(0-1), Fire(2-3), Earth(4-5), Metal(6-7), Water(8-9)
_TEN_DEITIES: Dict[str, List[Tuple[str, str, str]]] = {
    "Wood": [
        ("Wood", ""),
        ("Fire", "食神/伤官"),
        ("Earth", "正财/偏财"),
        ("Metal", "正官/七杀"),
        ("Water", "正印/偏印"),
    ],
    "Fire": [
        ("Wood", "正印/偏印"),
        ("Fire", ""),
        ("Earth", "食神/伤官"),
        ("Metal", "正财/偏财"),
        ("Water", "正官/七杀"),
    ],
    "Earth": [
        ("Wood", "正官/七杀"),
        ("Fire", "正印/偏印"),
        ("Earth", ""),
        ("Metal", "食神/伤官"),
        ("Water", "正财/偏财"),
    ],
    "Metal": [
        ("Wood", "正财/偏财"),
        ("Fire", "正官/七杀"),
        ("Earth", "正印/偏印"),
        ("Metal", ""),
        ("Water", "食神/伤官"),
    ],
    "Water": [
        ("Wood", "食神/伤官"),
        ("Fire", "正财/偏财"),
        ("Earth", "正官/七杀"),
        ("Metal", "正印/偏印"),
        ("Water", ""),
    ],
}

_SOLAR_TERM_NAMES = [
    "Li Chun", "Yu Shui", "Jing Zhe", "Chun Fen",
    "Qing Ming", "Gu Yu", "Li Xia", "Xiao Man",
    "Mang Zhong", "Xia Zhi", "Xiao Shu", "Da Shu",
    "Li Qiu", "Chu Shu", "Bai Lu", "Qiu Fen",
    "Han Lu", "Shuang Jiang", "Li Dong", "Xiao Xue",
    "Da Xue", "Dong Zhi", "Xiao Han", "Da Han",
]

# Major solar terms (month boundaries): every other term starting from 0
_MAJOR_TERMS = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]

# ======================================================================
# BaZi Engine
# ======================================================================


class BaZiEngine:
    @staticmethod
    def _solar_term_jds(year: int) -> List[float]:
        """Find Julian days for the 12 major solar terms of *year*.

        Major terms are at Sun longitudes: 315°, 345°, 15°, 45°, 75°, … 285°.
        """
        result = []
        target_lons = [(315 + 30 * i) % 360 for i in range(12)]
        # Search from Dec of previous year to Dec of current year
        start_jd = swe.julday(year - 1, 12, 1, 0.0)
        for target in target_lons:
            lo, hi = start_jd, start_jd + 400
            for _ in range(60):
                mid = (lo + hi) / 2.0
                sun = swe.calc_ut(mid, swe.SUN)[0][0]
                diff = (sun - target + 180) % 360 - 180
                if abs(diff) < 0.0001:
                    result.append(mid)
                    start_jd = mid
                    break
                if diff > 0:
                    hi = mid
                else:
                    lo = mid
            else:
                result.append(start_jd + 30)
        return result

    @staticmethod
    def _true_solar_hour(jd: float, lon: float, tz_offset: float) -> float:
        """Calculate True Solar Time (local apparent time) in decimal hours.

        Corrects zone time for longitude offset from standard meridian and
        the equation of time.
        """
        ut_hour = ((jd + 0.5) % 1.0) * 24.0
        zone_hour = (ut_hour + tz_offset) % 24.0
        std_meridian = tz_offset * 15.0
        lon_corr = (lon - std_meridian) / 15.0
        eq_of_time = swe.time_equ(jd) * 24.0
        return (zone_hour + lon_corr + eq_of_time) % 24.0

    @staticmethod
    def _find_major_term(year: int, target_lon: float) -> float:
        """Find the JD when the Sun reaches *target_lon*° in *year*."""
        start = swe.julday(year, 1, 1, 0.0)
        lo, hi = start, start + 370.0
        for _ in range(60):
            mid = (lo + hi) / 2.0
            sun = swe.calc_ut(mid, swe.SUN)[0][0]
            diff = (sun - target_lon + 180) % 360 - 180
            if abs(diff) < 0.0001:
                return mid
            if diff > 0:
                hi = mid
            else:
                lo = mid
        return lo

    _MAJOR_LONS = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285]

    @staticmethod
    def calculate(jd: float, lat: float, lon: float, tz_offset: float) -> Dict[str, Any]:
        # ✅ แก้ไขตรงนี้: ใช้ swe.revjul(jd) เพื่อดึงปี ค.ศ. รองรับปีก่อน 1970 บน Windows
        year, _, _, _ = swe.revjul(jd)
        true_solar_hour = BaZiEngine._true_solar_hour(jd, lon, tz_offset)

        raw_terms = [(BaZiEngine._find_major_term(year, l), i) for i, l in enumerate(BaZiEngine._MAJOR_LONS)]
        raw_terms.sort(key=lambda x: x[0])

        month_idx = 0
        for tjd, orig_idx in raw_terms:
            if jd >= tjd:
                month_idx = orig_idx

        li_chun_jd = next(tjd for tjd, oi in raw_terms if oi == 0)
        y_stem = (year - 4) % 10
        y_branch = (year - 4) % 12
        if jd < li_chun_jd:
            y_stem = (year - 5) % 10
            y_branch = (year - 5) % 12

        m_branch = (month_idx + 2) % 12
        y_mod = y_stem % 10
        m_first_stem = (y_mod * 2 + 2) % 10
        m_stem = (m_first_stem + month_idx) % 10

        jd_int = int(jd + 0.5)
        d_stem = (jd_int + 9) % 10
        d_branch = (jd_int + 1) % 12

        h_branch = (int((true_solar_hour + 1) % 24) // 2) % 12
        d_mod = d_stem % 10
        h_first_stem = (d_mod * 2) % 10
        h_stem = (h_first_stem + h_branch) % 10

        def _hidden(b: int) -> List[int]:
            return HIDDEN_STEMS.get(b, [])

        dm_elem = HEAVENLY_STEMS[d_stem][2]
        deities = []
        for stem in [y_stem, m_stem, d_stem, h_stem]:
            elem = HEAVENLY_STEMS[stem][2]
            for row in _TEN_DEITIES.get(dm_elem, []):
                if row[0] == elem:
                    deities.append(row[1] if row[1] else "Day Master")
                    break
            else:
                deities.append("")

        elem_count = {"Wood": 0, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 0}
        for stem in [y_stem, m_stem, d_stem, h_stem]:
            e = HEAVENLY_STEMS[stem][2]
            elem_count[e] = elem_count.get(e, 0) + 1
        for branch in [y_branch, m_branch, d_branch, h_branch]:
            e = EARTHLY_BRANCHES[branch][2]
            elem_count[e] = elem_count.get(e, 0) + 1
            for hs in _hidden(branch):
                e2 = HEAVENLY_STEMS[hs][2]
                elem_count[e2] = elem_count.get(e2, 0) + 0.5

        def _stem_name(idx: int) -> Dict[str, Any]:
            s = HEAVENLY_STEMS[idx % 10]
            return {"pinyin": s[0], "cn": s[1], "element": s[2], "index": idx % 10}

        def _branch_name(idx: int) -> Dict[str, Any]:
            b = EARTHLY_BRANCHES[idx % 12]
            return {"pinyin": b[0], "cn": b[1], "element": b[2], "index": idx % 12}

        return {
            "true_solar_time": round(true_solar_hour % 24, 4),
            "solar_term_index": month_idx,
            "solar_term_name": _SOLAR_TERM_NAMES[month_idx * 2] if month_idx * 2 < len(_SOLAR_TERM_NAMES) else "",
            "four_pillars": {
                "year": {"stem": _stem_name(y_stem), "branch": _branch_name(y_branch), "hidden_stems": [_stem_name(h) for h in _hidden(y_branch)]},
                "month": {"stem": _stem_name(m_stem), "branch": _branch_name(m_branch), "hidden_stems": [_stem_name(h) for h in _hidden(m_branch)]},
                "day": {"stem": _stem_name(d_stem), "branch": _branch_name(d_branch), "hidden_stems": [_stem_name(h) for h in _hidden(d_branch)]},
                "hour": {"stem": _stem_name(h_stem), "branch": _branch_name(h_branch), "hidden_stems": [_stem_name(h) for h in _hidden(h_branch)]},
            },
            "day_master": _stem_name(d_stem),
            "ten_deities": [
                {"stem": _stem_name(y_stem), "deity": deities[0]},
                {"stem": _stem_name(m_stem), "deity": deities[1]},
                {"stem": _stem_name(d_stem), "deity": deities[2]},
                {"stem": _stem_name(h_stem), "deity": deities[3]},
            ],
            "five_elements": {k: round(v, 1) for k, v in sorted(elem_count.items(), key=lambda x: -x[1])},
        }


# ======================================================================
# Western Engine
# ======================================================================

_PLANET_NAMES = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
]

_PLANET_IDS = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
               swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]

_SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


class WesternEngine:
    @staticmethod
    def calculate(jd: float, lat: float, lon: float) -> Dict[str, Any]:
        # Placidus is undefined near the poles; fall back rather than crash.
        try:
            houses_result = swe.houses(jd, lat, lon, b'P')
            house_system = "Placidus"
        except swe.Error:
            try:
                houses_result = swe.houses(jd, lat, lon, b'O')  # Porphyry
                house_system = "Porphyry"
            except swe.Error:
                houses_result = swe.houses(jd, lat, lon, b'W')  # Whole sign
                house_system = "Whole sign"
        asc = houses_result[1][0]
        mc = houses_result[1][1]
        house_cusps = list(houses_result[0])
        # pyswisseph รุ่นเก่าคืน cusps 13 ตัว (index 0 = 0.00 ไม่ได้ใช้)
        # ถ้าไม่ตัดทิ้ง เลขเรือนที่พิมพ์จะเพี้ยนไป 1 ตำแหน่ง (House 1 = 0.00,
        # House 2 = ลัคนา) และ reading.py จะหาเรือนของดาวผิดทั้งหมด
        if len(house_cusps) == 13 and house_cusps[0] == 0:
            house_cusps = house_cusps[1:]

        planets = {}
        for name, pid in zip(_PLANET_NAMES, _PLANET_IDS):
            pos = swe.calc_ut(jd, pid)[0][0]
            sign_idx = int(pos // 30)
            planets[name] = {
                "degree": round(pos, 4),
                "sign": _SIGN_NAMES[sign_idx],
                "sign_degree": round(pos % 30, 4),
            }

        # Aspects
        aspects = []
        orb = 8.0
        aspect_types = [
            (0, "Conjunction"), (60, "Sextile"), (90, "Square"),
            (120, "Trine"), (150, "Quincunx"), (180, "Opposition"),
        ]
        for i in range(len(_PLANET_NAMES)):
            for j in range(i + 1, len(_PLANET_NAMES)):
                diff = abs(planets[_PLANET_NAMES[i]]["degree"] - planets[_PLANET_NAMES[j]]["degree"])
                if diff > 180:
                    diff = 360 - diff
                for angle, name in aspect_types:
                    if abs(diff - angle) <= orb:
                        aspects.append({
                            "planet1": _PLANET_NAMES[i],
                            "planet2": _PLANET_NAMES[j],
                            "aspect": name,
                            "angle": round(diff, 2),
                            "orb": round(abs(diff - angle), 2),
                        })
                        break

        return {
            "ascendant": round(asc, 4),
            "midheaven": round(mc, 4),
            "houses": [round(c, 4) for c in house_cusps],
            "house_system": house_system,
            "planets": planets,
            "aspects": aspects,
        }


# ======================================================================
# Vedic Engine
# ======================================================================

_NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
    "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

_NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury", "Ketu",
    "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury", "Ketu", "Venus",
    "Sun", "Moon", "Mars", "Rahu", "Jupiter",
    "Saturn", "Mercury",
]

_RASHI_NAMES_SA = [
    "Mesha", "Vrishabha", "Mithuna", "Karka",
    "Simha", "Kanya", "Tula", "Vrishchika",
    "Dhanu", "Makara", "Kumbha", "Meena",
]

_D9_SIGNS = {
    0: [0, 5, 0, 5, 0, 5, 0, 5, 0],
    1: [1, 6, 1, 6, 1, 6, 1, 6, 1],
    2: [2, 7, 2, 7, 2, 7, 2, 7, 2],
    3: [3, 8, 3, 8, 3, 8, 3, 8, 3],
    4: [4, 9, 4, 9, 4, 9, 4, 9, 4],
    5: [5, 10, 5, 10, 5, 10, 5, 10, 5],
    6: [6, 11, 6, 11, 6, 11, 6, 11, 6],
    7: [7, 0, 7, 0, 7, 0, 7, 0, 7],
    8: [8, 1, 8, 1, 8, 1, 8, 1, 8],
    9: [9, 2, 9, 2, 9, 2, 9, 2, 9],
    10: [10, 3, 10, 3, 10, 3, 10, 3, 10],
    11: [11, 4, 11, 4, 11, 4, 11, 4, 11],
}


class VedicEngine:
    @staticmethod
    def calculate(jd: float) -> Dict[str, Any]:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        planets = {}
        for name, pid in zip(_PLANET_NAMES, _PLANET_IDS):
            pos = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]
            sign_idx = int(pos // 30)
            nakshatra_idx = int(pos // (360.0 / 27))
            pada = int((pos % (360.0 / 27)) // (360.0 / 27 / 4)) + 1
            d9_sign_idx = _D9_SIGNS[sign_idx][pada - 1]

            planets[name] = {
                "sidereal_degree": round(pos, 4),
                "rashi": _RASHI_NAMES_SA[sign_idx],
                "rashi_index": sign_idx,
                "nakshatra": _NAKSHATRA_NAMES[nakshatra_idx],
                "nakshatra_lord": _NAKSHATRA_LORDS[nakshatra_idx],
                "nakshatra_idx": nakshatra_idx,
                "pada": pada,
                "navamsha_rashi": _RASHI_NAMES_SA[d9_sign_idx],
                "navamsha_rashi_index": d9_sign_idx,
            }

        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY)
        return {"planets": planets}


# ======================================================================
# Human Design Constants & Cross Database
# ======================================================================

GATE_SEQUENCE = [
    25, 17, 21, 51, 42, 3, 27, 24, 2, 23, 8, 20,
    16, 35, 45, 12, 15, 52, 39, 53, 62, 56, 31, 33,
    7, 4, 29, 59, 40, 64, 47, 6, 46, 18, 48, 57,
    32, 50, 28, 44, 1, 43, 14, 34, 9, 5, 26, 11,
    10, 58, 38, 54, 61, 60, 41, 19, 13, 49, 30, 55,
    37, 63, 22, 36,
]

HD_START_DEGREE = 358.25

CENTERS: Dict[str, List[int]] = {
    "Head": [61, 63, 64],
    "Ajna": [4, 11, 17, 24, 43, 47],
    "Throat": [8, 12, 16, 20, 23, 31, 33, 35, 45, 56, 62],
    "Self": [1, 2, 7, 10, 13, 15, 25, 46],
    "Sacral": [3, 5, 9, 14, 27, 29, 34, 42, 59],
    "Root": [19, 28, 38, 39, 41, 52, 53, 54, 58, 60],
    "Spleen": [18, 28, 32, 44, 48, 50, 57],
    "Solar Plexus": [6, 22, 30, 36, 37, 49, 55],
    "Heart": [21, 26, 40, 51],
}

CHANNELS: List[Tuple[int, int]] = [
    (1, 8), (2, 14), (3, 60), (4, 63), (5, 15),
    (6, 59), (7, 31), (9, 52), (10, 20), (11, 56),
    (12, 22), (13, 33), (16, 48), (17, 62), (18, 58),
    (19, 49), (20, 34), (20, 57), (21, 45), (23, 43),
    (24, 61), (25, 51), (26, 44), (27, 50), (28, 38),
    (29, 46), (30, 41), (32, 54), (34, 57), (35, 36),
    (37, 40), (39, 55), (42, 53), (47, 64),
]

# Database ชื่อ Incarnation Cross แยกตาม Gate ของ Personality Sun
# (Right Angle Name, Left Angle Name, Juxtaposition Name)
CROSS_NAMES: Dict[int, Tuple[str, str, str]] = {
    1: ("The Sphinx", "Wishes", "Self-Expression"),
    2: ("The Sphinx", "Driver", "Direction"),
    3: ("Laws", "Mutation", "Mutating"),
    4: ("Explanation", "Prevention", "Formulization"),
    5: ("Consciousness", "Separation", "Habits"),
    6: ("Eden", "Plane", "Conflict"),
    7: ("The Sphinx", "Masks", "Interaction"),
    8: ("Contagion", "Uncertainty", "Style"),
    9: ("Planning", "Identification", "Focus"),
    10: ("Vessel of Love", "Prevention", "Behavior"),
    11: ("Eden", "Education", "Ideas"),
    12: ("Eden", "Articulation", "Articulation"),
    13: ("The Sphinx", "Listening", "Listening"),
    14: ("Contagion", "Individualism", "Empowering"),
    15: ("Vessel of Love", "Prevention", "Extremes"),
    16: ("Planning", "Experimentation", "Experimentation"),
    17: ("Service", "Upheaval", "Opinions"),
    18: ("Service", "Upheaval", "Correcting"),
    19: ("Four Ways", "Refinement", "Need"),
    20: ("Sleeping Phoenix", "Dualities", "Presenting"),
    21: ("Tension", "Endeavour", "Control"),
    22: ("Rulership", "Informing", "Grace"),
    23: ("Explanation", "Dedication", "Assimilation"),
    24: ("Four Ways", "Incarnation", "Rationalization"),
    25: ("Vessel of Love", "Healing", "Innocence"),
    26: ("Rulership", "Confrontation", "Trickery"),
    27: ("Unexpected", "Alignment", "Caring"),
    28: ("Unexpected", "Alignment", "Risk"),
    29: ("Contagion", "Industry", "Commitment"),
    30: ("Contagion", "Industry", "Fates"),
    31: ("Unexpected", "Alpha", "Influence"),
    32: ("Maya", "Limitation", "Conservation"),
    33: ("Four Ways", "Refinement", "Retreat"),
    34: ("Sleeping Phoenix", "Dualities", "Power"),
    35: ("Consciousness", "Separation", "Experience"),
    36: ("Eden", "Crisis", "Fate"),
    37: ("Planning", "Migration", "Bargaining"),
    38: ("Tension", "Individualism", "Opposition"),
    39: ("Tension", "Individualism", "Provocation"),
    40: ("Planning", "Migration", "Denial"),
    41: ("Unexpected", "Alpha", "Fantasy"),
    42: ("Maya", "Limitation", "Completion"),
    43: ("Explanation", "Dedication", "Insight"),
    44: ("Four Ways", "Incarnation", "Alertness"),
    45: ("Rulership", "Confrontation", "Possession"),
    46: ("Vessel of Love", "Healing", "Serendipity"),
    47: ("Rulership", "Informing", "Oppression"),
    48: ("Service", "Depth", "Depth"),
    49: ("Explanation", "Revolution", "Principles"),
    50: ("Laws", "Wishes", "Values"),
    51: ("Initiation", "Trump", "Shock"),
    52: ("Service", "Demand", "Stillness"),
    53: ("Penetration", "Cycles", "Beginnings"),
    54: ("Penetration", "Cycles", "Ambition"),
    55: ("Sleeping Phoenix", "Spirit", "Moods"),
    56: ("Laws", "Distraction", "Stimulation"),
    57: ("Penetration", "Trump", "Intuition"),
    58: ("Service", "Demand", "Vitality"),
    59: ("Sleeping Phoenix", "Spirit", "Strategy"),
    60: ("Laws", "Limitation", "Acceptance"),
    61: ("Consciousness", "Thinking", "Thinking"),
    62: ("Maya", "Obscuration", "Detail"),
    63: ("Consciousness", "Dominion", "Doubt"),
    64: ("Maya", "Dominion", "Confusion"),
}

_PLANET_NAMES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
_PLANET_IDS = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]


# ======================================================================
# Fully Complete Human Design Engine
# ======================================================================

class HDEngine:
    @staticmethod
    def calculate(jd_p: float) -> Dict[str, Any]:
        def _dgl(degree: float) -> Tuple[int, int, int, int]:
            gate_size = 360.0 / 64.0
            line_size = gate_size / 6.0
            color_size = line_size / 6.0
            tone_size = color_size / 6.0
            
            adjusted = (degree - HD_START_DEGREE) % 360.0
            index = int(adjusted / gate_size)
            line = int((adjusted % gate_size) / line_size) + 1
            color = int((adjusted % line_size) / color_size) + 1
            tone = int((adjusted % color_size) / tone_size) + 1
            return GATE_SEQUENCE[index], line, color, tone

        def _planet_positions(jd: float) -> Dict[str, Dict[str, Any]]:
            results = {}
            for name, pid in zip(_PLANET_NAMES, _PLANET_IDS):
                deg = swe.calc_ut(jd, pid)[0][0]
                g, l, c, t = _dgl(deg)
                results[name] = {"degree": deg, "gate": g, "line": l, "color": c, "tone": t}
            
            nn_deg = swe.calc_ut(jd, swe.TRUE_NODE)[0][0]
            g, l, c, t = _dgl(nn_deg)
            results["N.Node"] = {"degree": nn_deg, "gate": g, "line": l, "color": c, "tone": t}
            
            earth_deg = (results["Sun"]["degree"] + 180) % 360
            g, l, c, t = _dgl(earth_deg)
            results["Earth"] = {"degree": earth_deg, "gate": g, "line": l, "color": c, "tone": t}
            
            sn_deg = (nn_deg + 180) % 360
            g, l, c, t = _dgl(sn_deg)
            results["S.Node"] = {"degree": sn_deg, "gate": g, "line": l, "color": c, "tone": t}
            return results

        # 1. คำนวณเวลา Design (ประมาณ 88 วันก่อนเกิด)
        p_sun_deg = swe.calc_ut(jd_p, swe.SUN)[0][0]
        target_deg = (p_sun_deg - 88) % 360
        jd_low, jd_high = jd_p - 100, jd_p - 80
        jd_d = jd_low
        for _ in range(50):
            jd_d = (jd_low + jd_high) / 2.0
            sd = swe.calc_ut(jd_d, swe.SUN)[0][0]
            diff = (sd - target_deg + 180) % 360 - 180
            if abs(diff) < 0.0001:
                break
            if diff > 0:
                jd_high = jd_d
            else:
                jd_low = jd_d

        personality = _planet_positions(jd_p)
        design = _planet_positions(jd_d)
        
        all_gates = list(set(p["gate"] for p in personality.values()) | set(p["gate"] for p in design.values()))
        gate_set = set(all_gates)

        # 2. หา Defined Centers & Channels
        defined_centers: Set[str] = set()
        active_channels: List[Tuple[int, int]] = []
        center_map = {g: c for c, gates in CENTERS.items() for g in gates}
        
        for g1, g2 in CHANNELS:
            if g1 in gate_set and g2 in gate_set:
                active_channels.append((g1, g2))
                c1, c2 = center_map.get(g1), center_map.get(g2)
                if c1 and c2:
                    defined_centers.add(c1)
                    defined_centers.add(c2)

        # 3. คำนวณ Type, Strategy, Signature, Not-Self Theme
        has_sacral = "Sacral" in defined_centers
        motor_centers = {"Sacral", "Heart", "Solar Plexus", "Root"}
        
        graph: Dict[str, Set[str]] = {c: set() for c in CENTERS}
        for g1, g2 in active_channels:
            c1, c2 = center_map.get(g1), center_map.get(g2)
            if c1 and c2:
                graph[c1].add(c2)
                graph[c2].add(c1)

        motor_to_throat = False
        if "Throat" in defined_centers:
            visited, queue = set(), ["Throat"]
            while queue:
                cur = queue.pop(0)
                if cur in visited:
                    continue
                visited.add(cur)
                if cur in motor_centers:
                    motor_to_throat = True
                    break
                queue.extend(list(graph.get(cur, set()) - visited))

        if has_sacral and motor_to_throat:
            hd_type = "Manifesting Generator"
            strategy = "Wait to Respond"
            signature = "Satisfaction"
            not_self = "Frustration"
        elif has_sacral:
            hd_type = "Generator"
            strategy = "Wait to Respond"
            signature = "Satisfaction"
            not_self = "Frustration"
        elif motor_to_throat:
            hd_type = "Manifestor"
            strategy = "To Inform"
            signature = "Peace"
            not_self = "Anger"
        elif len(defined_centers) > 0:
            hd_type = "Projector"
            strategy = "Wait for Recognition and the Invitation"
            signature = "Success"
            not_self = "Bitterness"
        else:
            hd_type = "Reflector"
            strategy = "Wait a Lunar Cycle (28 Days)"
            signature = "Surprise"
            not_self = "Disappointment"

        # 4. คำนวณ Authority
        auth_priority = [
            ("Solar Plexus", "Solar Plexus"),
            ("Sacral", "Sacral"),
            ("Spleen", "Splenic"),
            ("Heart", "Ego"),
            ("Self", "Self Projected")
        ]
        authority = "Mental/Outer" if hd_type == "Projector" else ("Environmental" if hd_type == "Reflector" else "None")
        for center, a in auth_priority:
            if center in defined_centers:
                authority = a
                break

        # 5. คำนวณ Definition (Single, Split, Triple Split, Quadruple Split)
        def_centers_list = list(defined_centers)
        visited_centers = set()
        components_count = 0
        
        for c in def_centers_list:
            if c not in visited_centers:
                components_count += 1
                q = [c]
                while q:
                    curr = q.pop(0)
                    if curr not in visited_centers:
                        visited_centers.add(curr)
                        q.extend([nbr for nbr in graph[curr] if nbr in defined_centers and nbr not in visited_centers])
        
        if len(defined_centers) == 0:
            definition = "None"
        elif components_count == 1:
            definition = "Single"
        elif components_count == 2:
            definition = "Split"
        elif components_count == 3:
            definition = "Triple Split"
        else:
            definition = "Quadruple Split"

        # 6. คำนวณ Profile & Incarnation Cross (แมปชื่อเฉพาะแบบเต็ม)
        p_sun_line = personality['Sun']['line']
        d_sun_line = design['Sun']['line']
        profile = f"{p_sun_line}/{d_sun_line}"
        
        p_sun_gate = personality['Sun']['gate']
        p_earth_gate = personality['Earth']['gate']
        d_sun_gate = design['Sun']['gate']
        d_earth_gate = design['Earth']['gate']
        
        # หาประเภทย่อยของ Cross
        if profile == "4/1":
            cross_type_str = "Juxtaposition Cross"
            cross_name = CROSS_NAMES.get(p_sun_gate, ("Unknown", "Unknown", "Unknown"))[2]
        elif profile in ["1/3", "1/4", "2/4", "2/5", "3/5", "3/6", "4/6"]:
            cross_type_str = "Right Angle Cross"
            cross_name = CROSS_NAMES.get(p_sun_gate, ("Unknown", "Unknown", "Unknown"))[0]
        else:
            cross_type_str = "Left Angle Cross"
            cross_name = CROSS_NAMES.get(p_sun_gate, ("Unknown", "Unknown", "Unknown"))[1]
        
        incarnation_cross = f"{cross_type_str} of {cross_name} ({p_sun_gate}/{p_earth_gate} | {d_sun_gate}/{d_earth_gate})"

        # 7. คำนวณ Variable (PLL DRR)
        def get_arrow(tone: int) -> str:
            return "L" if tone in [1, 2, 3] else "R"

        v1 = get_arrow(personality['Sun']['tone'])
        v2 = get_arrow(personality['N.Node']['tone'])
        v3 = get_arrow(design['Sun']['tone'])
        v4 = get_arrow(design['N.Node']['tone'])
        variable = f"P{v1}{v2} D{v3}{v4}"

        return {
            "type": hd_type,
            "strategy": strategy,
            "signature": signature,
            "not_self_theme": not_self,
            "authority": authority,
            "definition": definition,
            "incarnation_cross": incarnation_cross,
            "profile": profile,
            "variable": variable,
            "defined_centers": sorted(defined_centers),
            "undefined_centers": sorted(set(CENTERS.keys()) - defined_centers),
            "active_channels": active_channels,
            "all_active_gates": sorted(all_gates),
            "personality": personality,
            "design": design,
        }


import pprint
from datetime import datetime
import swisseph as swe
import json
import os
import sys

# ======================================================================
# Main Execution Runner
# ======================================================================


def run_full_astronomical_profile(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    lat: float,
    lon: float,
    tz_offset: float,
    ephe_path: str | None = None,
):
    """ฟังก์ชันดึงค่าและแสดงผลลัพธ์ของทั้ง 4 ระบบออกมาทั้งหมด."""

    # ephe_path: ถ้าโฟลเดอร์ wor/data (ข้างๆ scripts/) มีไฟล์ .se1 → ใช้ไฟล์นั้น
    #   ไม่งั้นย้อนกลับไปค่า default เดิม ("data/ephe")
    if ephe_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        wor_data = os.path.join(script_dir, "..", "data")
        ephe_path = wor_data if os.path.isdir(wor_data) else "data/ephe"

    # 2. สั่งให้ Swiss Ephemeris โหลดไฟล์ข้อมูลสัตตดาราศาสตร์จากโฟลเดอร์นี้
    swe.set_ephe_path(ephe_path)

    local_decimal_hour = hour + (minute / 60.0)
    utc_decimal_hour = local_decimal_hour - tz_offset
    jd = swe.julday(year, month, day, utc_decimal_hour)

    print("=" * 60)
    print(f" PROFILE CALCULATION FOR: {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d} (UTC{tz_offset:+=.1f})")
    print(f" Location: Lat {lat}, Lon {lon} | Julian Day: {jd:.4f}")
    print("=" * 60)

    # 2. คำนวณผลลัพธ์ทั้ง 4 ระบบ
    bazi_data = BaZiEngine.calculate(jd, lat, lon, tz_offset)
    western_data = WesternEngine.calculate(jd, lat, lon)
    vedic_data = VedicEngine.calculate(jd)
    hd_data = HDEngine.calculate(jd)

    # ==================================================================
    # 1. BAZI (โป๊ยหยี่สี่เสา)
    # ==================================================================
    print("\n" + "☯" * 25 + " 1. BAZI PROFILE " + "☯" * 25)
    print(f"True Solar Time : {bazi_data['true_solar_time']} hrs")
    print(f"Solar Term      : {bazi_data['solar_term_name']} (Index {bazi_data['solar_term_index']})")
    print(f"Day Master      : {bazi_data['day_master']['pinyin']} ({bazi_data['day_master']['cn']}) - {bazi_data['day_master']['element']}")
    
    print("\n--- FOUR PILLARS ---")
    for pillar_name in ["year", "month", "day", "hour"]:
        p = bazi_data["four_pillars"][pillar_name]
        hidden = ", ".join([f"{h['pinyin']}({h['element']})" for h in p["hidden_stems"]])
        print(f"  {pillar_name.upper():<6}: Stem = {p['stem']['pinyin']}({p['stem']['cn']}/{p['stem']['element']}) | "
              f"Branch = {p['branch']['pinyin']}({p['branch']['cn']}/{p['branch']['element']}) | "
              f"Hidden = [{hidden}]")

    print("\n--- TEN DEITIES ---")
    for td in bazi_data["ten_deities"]:
        print(f"  Stem {td['stem']['pinyin']} ({td['stem']['element']}): {td['deity']}")

    print("\n--- FIVE ELEMENTS COUNT ---")
    for elem, count in bazi_data["five_elements"].items():
        print(f"  {elem:<8}: {count}")

    # ==================================================================
    # 2. WESTERN ASTROLOGY (โหราศาสตร์ตะวันตก)
    # ==================================================================
    print("\n" + "☸" * 25 + " 2. WESTERN ASTROLOGY " + "☸" * 25)
    print(f"Ascendant (AC) : {western_data['ascendant']:.2f}°")
    print(f"Midheaven (MC) : {western_data['midheaven']:.2f}°")
    
    print("\n--- PLANETARY POSITIONS ---")
    for planet, info in western_data["planets"].items():
        print(f"  {planet:<10}: {info['sign']:<12} at {info['sign_degree']:>6.2f}° (Total Degree: {info['degree']:.2f}°)")

    print("\n--- HOUSE CUSPS ---")
    print(f"  System: {western_data.get('house_system', 'Placidus')}")
    for idx, cusp in enumerate(western_data["houses"], 1):
        print(f"  House {idx:<2} : {cusp:.2f}°")

    print("\n--- ASPECTS ---")
    for asp in western_data["aspects"]:
        print(f"  {asp['planet1']:<8} {asp['aspect']:<12} {asp['planet2']:<8} (Angle: {asp['angle']}°, Orb: {asp['orb']}°)")

    # ==================================================================
    # 3. VEDIC ASTROLOGY (โหราศาสตร์ภารตะ/นิรายนะ)
    # ==================================================================
    print("\n" + "🕉" * 25 + " 3. VEDIC ASTROLOGY " + "🕉" * 25)
    print("--- SIDEREAL PLANETS & NAKSHATRAS ---")
    for planet, info in vedic_data["planets"].items():
        print(f"  {planet:<10}: Rashi = {info['rashi']:<10} | "
              f"Nakshatra = {info['nakshatra']} (Lord: {info['nakshatra_lord']}, Pada: {info['pada']}) | "
              f"Navamsha = {info['navamsha_rashi']}")

   # 4. HUMAN DESIGN (FULL SUMMARY DISPLAY)
    print("\n" + "✦" * 25 + " 4. HUMAN DESIGN " + "✦" * 25)
    print(f"Type             : {hd_data['type']}")
    print(f"Strategy         : {hd_data['strategy']}")
    print(f"Signature        : {hd_data['signature']}")
    print(f"Not-Self Theme   : {hd_data['not_self_theme']}")
    print(f"Authority        : {hd_data['authority']}")
    print(f"Definition       : {hd_data['definition']}")
    print(f"Incarnation Cross: {hd_data['incarnation_cross']}")
    print(f"Profile          : {hd_data['profile']}")
    print(f"Variable         : {hd_data['variable']}")
    
    print("\n--- CENTERS & CHANNELS ---")
    print(f"Defined Centers  : {', '.join(hd_data['defined_centers'])}")
    print(f"Undefined Centers: {', '.join(hd_data['undefined_centers'])}")
    print(f"Active Channels  : {hd_data['active_channels']}")
    print(f"Active Gates     : {hd_data['all_active_gates']}")

    print("\n--- PERSONALITY POSITIONS (BLACK) ---")
    for body, info in hd_data["personality"].items():
        print(f"  {body:<10}: Gate {info['gate']}.{info['line']} (Degree: {info['degree']:.2f}°)")

    print("\n--- DESIGN POSITIONS (RED) ---")
    for body, info in hd_data["design"].items():
        print(f"  {body:<10}: Gate {info['gate']}.{info['line']} (Degree: {info['degree']:.2f}°)")

    print("\n" + "=" * 65)


# ======================================================================
# สั่งรันโปรแกรม
# ======================================================================
if __name__ == "__main__":

    DEFAULT_INPUT = {
        "year": 1992,
        "month": 8,
        "day": 8,
        "hour": 16,
        "minute": 49,
        "lat": 6.53995,
        "lon": 101.29,
        "tz_offset": 7,
    }

    def _show_usage() -> None:
        print(
            "Usage: python astrology.py [year month day hour minute lat lon tz_offset]\n"
            "   or: WOR_INPUT='{\"year\":...,\"month\":...,\"day\":...,\"hour\":...,"
            "\"minute\":...,\"lat\":...,\"lon\":...,\"tz_offset\":...}' python astrology.py",
            file=sys.stderr,
        )

    input_data = DEFAULT_INPUT
    env_input = os.environ.get("WOR_INPUT")
    if env_input:
        try:
            input_data = json.loads(env_input)
        except json.JSONDecodeError as exc:
            print(f"Error: WOR_INPUT is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(1)
    elif sys.argv[1:]:
        args = sys.argv[1:]
        if len(args) != 8:
            _show_usage()
            sys.exit(1)
        try:
            input_data = {
                "year": int(args[0]),
                "month": int(args[1]),
                "day": int(args[2]),
                "hour": int(args[3]),
                "minute": int(args[4]),
                "lat": float(args[5]),
                "lon": float(args[6]),
                "tz_offset": float(args[7]),
            }
        except ValueError:
            _show_usage()
            sys.exit(1)

    print(
        f"# Chart for {input_data['year']}-{input_data['month']:02d}-{input_data['day']:02d} "
        f"{input_data['hour']:02d}:{input_data['minute']:02d} "
        f"(lat {input_data['lat']}, lon {input_data['lon']}, tz {input_data['tz_offset']:+.0f})"
    )

    run_full_astronomical_profile(
        year=input_data["year"],
        month=input_data["month"],
        day=input_data["day"],
        hour=input_data["hour"],
        minute=input_data["minute"],
        lat=input_data["lat"],
        lon=input_data["lon"],
        tz_offset=input_data["tz_offset"],
    )