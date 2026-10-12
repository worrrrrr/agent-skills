# BaZi / Four Pillars — Interpretation Reference

Used with the `bazi` section of `scripts/astrology.py` output. Thai: ปาจื่อ / โป๊ยหยี่สี่เสา / ดวงจีน.

## Day Master (日主 / 日元)

The **day-pillar stem** is the self. Its element is the core identity; its polarity colours how that identity acts.

| Polarity | Stems (index)                                                                      | Temperament                         |
| -------- | ---------------------------------------------------------------------------------- | ----------------------------------- |
| Yang 阳  | 甲 Jia(0) Wood, 丙 Bing(2) Fire, 戊 Wu(4) Earth, 庚 Geng(6) Metal, 壬 Ren(8) Water | Outward, active, initiating, direct |
| Yin 阴   | 乙 Yi(1) Wood, 丁 Ding(3) Fire, 己 Ji(5) Earth, 辛 Xin(7) Metal, 癸 Gui(9) Water   | Inward, receptive, adaptive, subtle |

Polarity = stem index parity (even = yang, odd = yin). The engine returns `index`, so you can always recover it.

## Five Elements (五行)

Wood 木 · Fire 火 · Earth 土 · Metal 金 · Water 水.

- **Generating 生 (sheng):** Wood → Fire → Earth → Metal → Water → Wood.
- **Controlling 克 (ke):** Wood → Earth → Water → Fire → Metal → Wood.

A "weak" Day Master benefits from the element that generates it (Resource) and the same element (Companion). A "strong" Day Master benefits from Output, Wealth, and Officer elements that drain or control it.

## Ten Deities (十神)

Relationship of every other stem to the Day Master. **The engine returns the combined category** (e.g. `正财/偏财`); to get direct vs indirect, compare the polarity of the two stems.

| Deity                             | Relationship to Day Master  | Polarity match | Meaning                                                |
| --------------------------------- | --------------------------- | -------------- | ------------------------------------------------------ |
| 比肩 Bi Jian — Companion          | same element                | same           | Self-reliance, peers, siblings, competition            |
| 劫财 Jie Cai — Rob Wealth         | same element                | different      | Rivalry, risk-taking, resource loss                    |
| 食神 Shi Shen — Eating God        | Day Master generates it     | same           | Talent, enjoyment, gentle expression                   |
| 伤官 Shang Guan — Hurting Officer | Day Master generates it     | different      | Brilliance, rebellion, performance, sharp tongue       |
| 偏财 Pian Cai — Indirect Wealth   | Day Master controls it      | same           | Windfall, opportunity, sociability, father             |
| 正财 Zheng Cai — Direct Wealth    | Day Master controls it      | different      | Steady income, diligence, spouse (for a male chart)    |
| 七杀 Qi Sha — Seven Killings      | it controls the Day Master  | same           | Pressure, authority, discipline, risk                  |
| 正官 Zheng Guan — Direct Officer  | it controls the Day Master  | different      | Career, rules, reputation, spouse (for a female chart) |
| 偏印 Pian Yin — Indirect Resource | it generates the Day Master | same           | Unconventional learning, intuition, isolation          |
| 正印 Zheng Yin — Direct Resource  | it generates the Day Master | different      | Support, education, nurture, mother                    |

Reading shortcut: **Resource** = support received · **Companion** = allies/self · **Output** = what you produce · **Wealth** = what you control · **Officer** = what controls you.

## The Four Pillars (四柱)

| Pillar   | Domain                                                                                               |
| -------- | ---------------------------------------------------------------------------------------------------- |
| Year 年  | Ancestry, early life, public/social image                                                            |
| Month 月 | Parents, career, social environment — **the strongest pillar**; its branch sets the solar-term month |
| Day 日   | Self (stem) and spouse/partner (branch)                                                              |
| Hour 时  | Children, late life, inner aspiration, legacy                                                        |

The **month pillar** governs the season the Day Master was born into and carries the most weight when judging strength. Month boundaries are **solar terms** (節氣), not calendar months — a birth a day before/after a term belongs to the neighbouring month.

## Five-element counts (caveat)

The engine counts each heavenly stem as 1, each branch as 1, and each hidden stem as 0.5. Treat the totals as a **rough balance indicator**, not an exact weight. Also read _which_ elements are missing, not just the totals.

## Reading order

1. State the Day Master (stem, element, polarity).
2. Judge strength: support (Resource + Companion) vs drain (Output + Wealth + Officer), weighting the month pillar most.
3. Name the dominant and missing elements.
4. Walk the ten deities, pillar by pillar.
5. Translate into plain language — career, relationships, temperament, timing — instead of reciting tables.
