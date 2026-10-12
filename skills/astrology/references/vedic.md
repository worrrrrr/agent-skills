# Vedic / Jyotish — Interpretation Reference

Used with the `vedic` section of `scripts/astrology.py` output. Sidereal zodiac, **Lahiri ayanamsa** (Thai: โหราศาสตร์ภารตะ / นิรายนะ).

## Tropical vs sidereal

Sidereal positions are shifted back from tropical by the **ayanamsa** (≈24° in the modern era). This is why a Vedic Sun sign is often one sign earlier than the Western one. Always read the engine's `sidereal_degree`, never the tropical value.

## Rashi (ราศี) — the 12 signs

| Index | Sanskrit   | Western     |
| ----- | ---------- | ----------- |
| 0     | Mesha      | Aries       |
| 1     | Vrishabha  | Taurus      |
| 2     | Mithuna    | Gemini      |
| 3     | Karka      | Cancer      |
| 4     | Simha      | Leo         |
| 5     | Kanya      | Virgo       |
| 6     | Tula       | Libra       |
| 7     | Vrishchika | Scorpio     |
| 8     | Dhanu      | Sagittarius |
| 9     | Makara     | Capricorn   |
| 10    | Kumbha     | Aquarius    |
| 11    | Meena      | Pisces      |

The **Moon's rashi** is the "Moon sign" (Janma Rashi) and is the primary reference in Jyotish; the **Sun's rashi** is secondary.

## Nakshatra (นักษัตร) — 27 lunar mansions

Each nakshatra spans **13°20′** and has a ruling planet (lord). The lord sequence follows the Vimshottari Dasha order: Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury, repeating three times.

| #   | Nakshatra       | Lord    | #   | Nakshatra         | Lord    |
| --- | --------------- | ------- | --- | ----------------- | ------- |
| 1   | Ashwini         | Ketu    | 15  | Swati             | Rahu    |
| 2   | Bharani         | Venus   | 16  | Vishakha          | Jupiter |
| 3   | Krittika        | Sun     | 17  | Anuradha          | Saturn  |
| 4   | Rohini          | Moon    | 18  | Jyeshtha          | Mercury |
| 5   | Mrigashira      | Mars    | 19  | Mula              | Ketu    |
| 6   | Ardra           | Rahu    | 20  | Purva Ashadha     | Venus   |
| 7   | Punarvasu       | Jupiter | 21  | Uttara Ashadha    | Sun     |
| 8   | Pushya          | Saturn  | 22  | Shravana          | Moon    |
| 9   | Ashlesha        | Mercury | 23  | Dhanishta         | Mars    |
| 10  | Magha           | Ketu    | 24  | Shatabhisha       | Rahu    |
| 11  | Purva Phalguni  | Venus   | 25  | Purva Bhadrapada  | Jupiter |
| 12  | Uttara Phalguni | Sun     | 26  | Uttara Bhadrapada | Saturn  |
| 13  | Hasta           | Moon    | 27  | Revati            | Mercury |
| 14  | Chitra          | Mars    |     |                   |         |

**Vimshottari dasha years** (planetary periods, used for timing): Ketu 7 · Venus 20 · Sun 6 · Moon 10 · Mars 7 · Rahu 18 · Jupiter 16 · Saturn 19 · Mercury 17 = 120 years. The nakshatra of the Moon sets the starting dasha.

## Pada (บาท) — the quarters

Each nakshatra divides into **4 padas** of 3°20′ each. The pada refines the reading and maps to the **Navamsha (D9)** sign the engine reports (`navamsha_rashi`). Navamsha is the traditional chart for marriage, dharma, and the inner strength of a planet.

## Reading order

1. Moon's rashi and nakshatra first (mind and emotional nature).
2. Nakshatra **lord** — its condition in the chart colours the whole nakshatra's expression.
3. Sun's rashi for soul/purpose; Ascendant if available.
4. Navamsha to check whether a planet is strengthened or weakened.
5. Note the ayanamsa value the engine reports so results are reproducible.
