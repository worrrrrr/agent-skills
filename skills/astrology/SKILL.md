---
name: astrology
description: Use when calculating or interpreting birth charts and full-spectrum astrological profiles — Western tropical natal charts, Vedic/sidereal (Lahiri) charts, Chinese BaZi / Four Pillars, and Human Design (gates, lines, type, authority, incarnation cross). Triggers on "natal chart", "birth chart", "horoscope", "โหราศาสตร์", "ดวง", "ปาจื่อ", "โป๊ยหยี่", "สี่เสา", "BaZi", "Four Pillars", "Human Design", "Vedic", "Jyotish", "sidereal", "nakshatra", or requests for planetary positions, houses, or gate activations from a birth date/time/location.
---

# Astrology — Full-Spectrum Chart Engine

Computes four systems from one birth input: **BaZi**, **Western tropical**, **Vedic sidereal**, and **Human Design**.

## Inputs (all systems)

| Field                  | Notes                                   |
| ---------------------- | --------------------------------------- |
| `year`, `month`, `day` | Calendar date, local civil time         |
| `hour`, `minute`       | 24-hour local civil time                |
| `lat`                  | Degrees, + North                        |
| `lon`                  | Degrees, + East                         |
| `tz_offset`            | UTC offset in hours, e.g. Thailand `+7` |

If any of date, time, or location is missing, ask the user — do not guess. Timezone/coordinate accuracy directly changes the Ascendant, house cusps, hour pillar, and all Human Design lines.

## Two engines — pick one

### 1. Python — authoritative (Swiss Ephemeris)

`scripts/astrology.py` uses `pyswisseph` for all planetary math and is the **source of truth**. Prefer this engine.

```sh
python scripts/astrology.py 1992 8 8 16 49 6.53995 101.29 7
# args: year month day hour minute lat lon tz_offset
```

Or pass JSON via env var (good for programmatic calls):

```sh
WOR_INPUT='{"year":1992,"month":8,"day":8,"hour":16,"minute":49,"lat":6.53995,"lon":101.29,"tz_offset":7}' python scripts/astrology.py
```

With no args and no env var it runs a built-in default chart.

**Ephemeris files:** the script looks for `.se1` data in `../data` relative to `scripts/`, then falls back to `data/ephe`. This repo stores them in `assets/`. To use the real Swiss Ephemeris files (rather than the Moshier fallback), call the function directly with the path:

```python
from astrology import run_full_astronomical_profile
run_full_astronomical_profile(1992, 8, 8, 16, 49, 6.53995, 101.29, 7,
                              ephe_path="assets")
```

Install dependency if missing: `pip install pyswisseph`.

### 1b. Python — Thai reading (interpretation layer)

`scripts/reading.py` imports the engines above and turns the raw output into a **plain-text Thai reading** covering all four systems. Use it when the user wants an actual reading (คำอ่าน/คำทำนาย), not just raw numbers.

```sh
python scripts/reading.py 1992 8 8 16 49 6.53995 101.29 7 m
# args: year month day hour minute lat lon tz_offset [gender]
# gender (m/f) is optional — needed for 大運 (Da Yun) direction
```

It auto-loads the bundled `assets/*.se1` ephemeris files. Its interpretation tables are in Thai (`ELEMENT_TH`, `DEITY_TH`, `NAKSHATRA_TH`, `TYPE_TH`, etc.) and can be extended in place. It also computes, for BaZi: **12 Life Stages (十二長生)**, **18 神煞 stars** (文昌/Intelligence, 太極貴人, 桃花, 驛馬, 華蓋, 干祿, 紅艷煞, …), **Na Yin (納音)**, **Kong Wang (空亡)**, **day-master strength** with favourable/avoid elements (喜用神/忌神), **Da Yun (大運)** 10-year cycles annotated with their ten-deity and favourable-element mark, **Liu Nian (流年)** annual pillars, and a final Thai **summary reading** (section 5) that ties BaZi + Human Design + Western together. The 神煞 use classical formulas (some schools differ); the rest are exact. `reading.py` computes the BaZi ten deities itself with correct polarity (direct vs indirect), because `astrology.py`'s built-in table labels every same-element stem as "Day Master".

Output covers: true solar time + four pillars + ten deities + five-element counts; Ascendant/MC, planets, Placidus cusps, aspects; sidereal rashi/nakshatra/pada/navamsha; and Human Design type, strategy, authority, definition, profile, incarnation cross, variable, centers, channels, and personality/design activations.

### 2. TypeScript — zero-dependency, approximate

`scripts/astro.ts` re-implements the same four systems with no dependencies, for environments without Python/Swiss Ephemeris. Run with `npx tsx scripts/astro.ts` — **but note it exports functions only; there is no CLI runner.** Write a small driver that imports it:

```ts
import { computeChart } from './astro';
const chart = computeChart({
	year: 1992,
	month: 8,
	day: 8,
	hour: 16,
	minute: 49,
	utcOffsetHours: 7,
	latitude: 6.53995,
	longitude: 101.29
});
console.log(chart);
```

Treat TS output as sign/gate-level only. Precision caveats are documented at the top of `astro.ts`: Sun ~0.01°, Moon ~0.1–0.3°, planets Keplerian (no perturbations, up to ~1° on outer planets), Placidus unreliable above ~66° latitude. **If a planet sits near a sign/house/gate boundary, say so and verify with the Python engine rather than asserting.**

## Interpreting results

The scripts **calculate only** — they output raw positions and classifications. The reading/interpretation is your job. Read the matching reference file before interpreting each system:

| System              | Reference                    | Read it for                                             |
| ------------------- | ---------------------------- | ------------------------------------------------------- |
| BaZi / Four Pillars | `references/bazi.md`         | Day Master, five elements, ten deities, pillar meanings |
| Western             | `references/western.md`      | Planets, signs, houses, aspects, angles                 |
| Vedic               | `references/vedic.md`        | Rashi, nakshatras, lords, padas, navamsha, ayanamsa     |
| Human Design        | `references/human-design.md` | Type, authority, definition, profile, centers, channels |

Load only the reference(s) for the system the user actually asked about. When the user asks for a full reading, run the engine, then walk each requested system using its reference and translate the output into plain language (Thai if the user writes Thai) rather than reciting raw tables.

System-specific notes:

- **BaZi** — month pillar changes at solar terms (not the 1st), so births near a term boundary need true solar time.
- **Western** — weight aspects by the orb the engine reports.
- **Vedic** — nakshatra lord and pada matter more than the rashi for prediction.
- **Human Design** — the Design timestamp is found by 88° of solar arc before birth, not exactly 88 days.

## Do not

- Do not invent planetary positions, gate numbers, or cross names — always run an engine.
- Do not present approximate TS output as ephemeris-grade.
- Do not assume a timezone; confirm it against the birth location and date (DST and historical offsets change results).
