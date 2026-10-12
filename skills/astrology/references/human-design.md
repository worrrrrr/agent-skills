# Human Design — Interpretation Reference

Used with the `humanDesign` section of `scripts/astrology.py` output. Thai: ฮิวแมนดีไซน์.

## Type, Strategy, Signature, Not-Self Theme

| Type                  | Strategy                          | Signature (flow) | Not-Self (resistance) |
| --------------------- | --------------------------------- | ---------------- | --------------------- |
| Generator             | Wait to Respond                   | Satisfaction     | Frustration           |
| Manifesting Generator | Wait to Respond, then Inform      | Satisfaction     | Frustration           |
| Manifestor            | To Inform                         | Peace            | Anger                 |
| Projector             | Wait for Recognition & Invitation | Success          | Bitterness            |
| Reflector             | Wait a Lunar Cycle (28 days)      | Surprise         | Disappointment        |

Type is decided by which centers are **defined** (Sacral defined → Generator family; a defined motor connected to the Throat without the Sacral → Manifestor; some centers defined without Sacral/motor-to-Throat → Projector; nothing defined → Reflector).

## Inner Authority — how to make decisions

| Authority                | Defined center   | Decision style                                              |
| ------------------------ | ---------------- | ----------------------------------------------------------- |
| Emotional / Solar Plexus | Solar Plexus     | Ride the emotional wave; never decide in the moment         |
| Sacral                   | Sacral           | Gut "uh-huh / nuh-uh" response in the now                   |
| Splenic                  | Spleen           | Instant quiet intuition, one-time signal                    |
| Ego / Heart              | Heart            | Willpower and what you truly want                           |
| Self-Projected           | Self (G)         | Truth spoken aloud to hear your own direction               |
| Mental / Outer           | none (Projector) | Talk it through with trusted others, then trust environment |
| Lunar / Environmental    | none (Reflector) | Wait 28 days, sample the environment                        |

The engine reports the **highest-priority defined center** among Solar Plexus → Sacral → Spleen → Heart → Self.

## Definition

How the defined centers connect into one or more groups:

- **Single** — all defined centers connected (self-contained processing).
- **Split** — two disconnected groups (seek the other half; bridging is life theme).
- **Triple Split** — three groups.
- **Quadruple Split** — four groups.
- **None** — Reflector.

## Profile — the personality/design line pairing

Profile = `Personality Sun line / Design Sun line` (e.g. `4/6`).

| Profile                           | Cross type    |
| --------------------------------- | ------------- |
| 1/3, 1/4, 2/4, 2/5, 3/5, 3/6, 4/6 | Right Angle   |
| 4/1                               | Juxtaposition |
| 5/1, 5/2, 6/2, 6/3                | Left Angle    |

Line meanings: 1 Investigator (need foundation) · 2 Hermit (natural gift, called out) · 3 Martyr/Experimenter (trial & error) · 4 Opportunist (community/network) · 5 Heretic (practical solutions, projections) · 6 Role Model (three life phases).

## Incarnation Cross

Formed from the Personality Sun/Earth and Design Sun/Earth gates. The engine reports the full label, e.g. `Right Angle Cross of Planning (9/16 | 40/37)`. Cross type follows the profile table above. Right Angle = personal destiny · Left Angle = transpersonal destiny · Juxtaposition = fixed, narrow focus.

## Centers — 9 energy hubs

| Center       | Function when defined                  |
| ------------ | -------------------------------------- |
| Head         | Inspiration, mental pressure           |
| Ajna         | Conceptualisation, way of thinking     |
| Throat       | Expression, action, manifestation      |
| Self (G)     | Identity, direction, love              |
| Sacral       | Life force, work energy, sexuality     |
| Heart (Ego)  | Willpower, worth, material world       |
| Solar Plexus | Emotions, feelings, spirit awareness   |
| Spleen       | Intuition, immune system, fear, health |
| Root         | Adrenaline, drive, pressure to act     |

**Defined** = consistent, reliable energy you radiate. **Undefined/open** = where you absorb and amplify others; a source of both wisdom and conditioning.

## Channels & Gates

- **64 gates** map the zodiac wheel; **36 channels** connect two gates across centers. A channel is active only when **both** its gates are activated (personality or design).
- The engine returns `active_channels`, `defined_centers`, and `all_active_gates`. A gate activated by only one side is a "hanging gate" — not a full channel.

## Variable

The engine reports a four-arrow code, e.g. `PLL DRR`: Personality (P) and Design (D), each with a **Digestion/Determination** arrow and a **Perspective/Environment** arrow (`L` = left/brain, `R` = right/brain). It is an advanced layer — mention only if the user asks for depth.

## Reading order

1. Type and Strategy (the headline).
2. Authority (the decision-making instruction).
3. Profile (life role) and Definition (how you process).
4. Incarnation Cross (life theme).
5. Defined vs open centers — where energy is reliable and where conditioning enters.
