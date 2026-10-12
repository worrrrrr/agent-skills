# Western Astrology — Interpretation Reference

Used with the `western` section of `scripts/astrology.py` output (tropical zodiac, Placidus houses). Thai: โหราศาสตร์ตะวันตก.

## Angles

- **Ascendant (AC / Rising)** — the persona, first impressions, how you meet the world. Sign + ruler colour the whole chart.
- **Midheaven (MC)** — career, public standing, life direction.

## Planets — what each signifies

| Planet  | Signifies                                     |
| ------- | --------------------------------------------- |
| Sun     | Core identity, ego, vitality, purpose         |
| Moon    | Emotion, instinct, inner needs, mother        |
| Mercury | Mind, communication, learning, commerce       |
| Venus   | Love, attraction, values, art, money          |
| Mars    | Drive, desire, courage, conflict, action      |
| Jupiter | Expansion, luck, belief, growth               |
| Saturn  | Structure, discipline, limitation, time, duty |
| Uranus  | Innovation, rebellion, sudden change, freedom |
| Neptune | Dreams, imagination, compassion, illusion     |
| Pluto   | Power, transformation, obsession, rebirth     |

## Signs — element and modality

Every sign = one **element** (how it acts) × one **modality** (how it initiates).

| Element | Signs                    | Style                                |
| ------- | ------------------------ | ------------------------------------ |
| Fire    | Aries, Leo, Sagittarius  | Passionate, spontaneous, will-driven |
| Earth   | Taurus, Virgo, Capricorn | Practical, grounded, sensory         |
| Air     | Gemini, Libra, Aquarius  | Mental, social, idea-driven          |
| Water   | Cancer, Scorpio, Pisces  | Emotional, intuitive, feeling-led    |

| Modality | Signs                              | Style                    |
| -------- | ---------------------------------- | ------------------------ |
| Cardinal | Aries, Cancer, Libra, Capricorn    | Initiates, starts things |
| Fixed    | Taurus, Leo, Scorpio, Aquarius     | Sustains, resists change |
| Mutable  | Gemini, Virgo, Sagittarius, Pisces | Adapts, transitions      |

## Houses — life areas

| House | Area                                              |
| ----- | ------------------------------------------------- |
| 1     | Self, body, persona (starts at AC)                |
| 2     | Money, possessions, self-worth                    |
| 3     | Communication, siblings, short trips              |
| 4     | Home, roots, family (starts at IC)                |
| 5     | Creativity, romance, children, play               |
| 6     | Work, health, routine, service                    |
| 7     | Partnership, marriage, open enemies (opposite AC) |
| 8     | Shared resources, intimacy, death, transformation |
| 9     | Philosophy, higher learning, travel, belief       |
| 10    | Career, status, public role (starts at MC)        |
| 11    | Friends, groups, hopes, community                 |
| 12    | Subconscious, solitude, endings, the unseen       |

A planet's **sign** = how it expresses; its **house** = where it plays out. The engine reports both the total degree and the degree within the sign.

## Aspects — angular relationships

| Angle | Aspect      | Nature                                   |
| ----- | ----------- | ---------------------------------------- |
| 0°    | Conjunction | Blended, intensified — strong either way |
| 60°   | Sextile     | Flowing, supportive, easy opportunity    |
| 90°   | Square      | Friction, tension, drives growth         |
| 120°  | Trine       | Harmonious, natural talent, ease         |
| 150°  | Quincunx    | Awkward, requires adjustment             |
| 180°  | Opposition  | Polarised, balancing act, awareness      |

The engine flags an aspect when within **8° orb** and reports the exact orb. Tighter orb = stronger. Weight conjunctions/oppositions/squares/trines above sextiles and quincunxes.

## Reading order

1. Note the Sun, Moon, and Ascendant ("the big three").
2. For each planet, combine sign (how) + house (where).
3. Pull the tightest aspects and describe them as dynamics, not verdicts.
4. Read the chart as a whole: dominant element, dominant modality, and any cluster of planets.
