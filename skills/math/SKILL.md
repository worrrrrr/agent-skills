---
name: math
description: Use when solving equations, symbolic calculus, constraint/SAT problems, or Swiss ephemeris astrology with sympy, z3-solver, pyswisseph. Triggers on keywords sympy, z3, swisseph, ephemeris, สมการ, โหราศาสตร์.
---

# Math Skill

Workflow for exact computation. Always run code with `python`, never guess output.

## Engine (source of truth)

`scripts/run.py` — one JSON-in/JSON-out entry for calc + sympy + z3:

```sh
python scripts/run.py '{"op":"calc","expr":"(1.05^20 - 1)/0.05"}'
python scripts/run.py '{"op":"solve","eq":"x**2 - 5*x + 6 = 0","symbol":"x"}'
python scripts/run.py '{"op":"solve","eq":"3**x = x**9","symbol":"x"}'
python scripts/run.py '{"op":"nsolve","eq":"3**x - x**9","symbol":"x","guesses":[1,27]}'
python scripts/run.py '{"op":"z3solve","vars":["x","y"],"eqs":["x + y == 10","x - y == 2"]}'
# raw problem — auto-router picks the op itself:
python scripts/run.py '{"op":"auto","q":"lim (1-cos(x))/x^2 x->0"}'
# batch file — one JSON/raw problem per line, results to file:
python scripts/run.py batch problems43.txt skilloutput.txt
# ops: calc | solve | nsolve | diff | integrate | limit | eigen | det | inv | simplify | sum | series | dsolve | factor | modsolve | residue | cfrac | nullspace | jordan | svd | matexp | z3solve | auto
```

`auto` รับโจทย์ดิบ (อังกฤษ/ไทย: lim, integrate, diff, sum, series, ODE แบบ y''/y', mod, factor, residue, cfrac, อสมการ, Diophantine) แล้วเลือก op เองพร้อมบอกว่า detect เป็นอะไร

`solve` accepts `=` equations, returns exact + exact_numeric + numeric (with residuals). `nsolve` sweeps guesses and dedups. Prefer the engine over hand-writing sympy/z3. Fall back to raw sympy/z3 below only for cases the engine does not cover.

## 1. sympy — exact/symbolic (equations, calculus, matrices)

```python
import sympy as sp
x = sp.symbols('x')
sp.solve(x**2 - 5*x + 6, x)          # exact roots
sp.diff(sp.sin(x)*sp.exp(x), x)      # calculus
sp.integrate(x**2, (x, 0, 1))
sp.Matrix([[1,2],[3,4]]).eigenvals()
```

Rules: use `sp.solve`/`solveset` for equations, `sp.simplify` to verify, `nsimplify` for numeric→exact. No `eval()` on strings.

## 2. z3 — constraints / SAT / prove

```python
from z3 import *
x, y = Ints('x y')
s = Solver()
s.add(x + y == 10, x - y == 2)
print(s.check(), s.model())   # sat + model
```

Rules: use `Solver()` + `check()`/`model()` for finding assignments, `prove()` for theorems. BitVec for bit logic, Optimize for optimization.

## 3. pyswisseph — ephemeris (Swiss Ephemeris)

```python
import swisseph as swe
swe.set_ephe_path('.')  # or path to .se1 files; Moshier fallback if missing
jd = swe.julday(2026, 10, 11, 12.0)
pos, _ = swe.calc_ut(jd, swe.SUN)   # longitude, latitude, distance...
print(pos[0])  # ecliptic longitude deg
```

Rules: JD via `swe.julday(y,m,d,hour_ut)`; planets `swe.SUN..swe.PLUTO`, `swe.calc_ut(jd, planet)`; houses `swe.houses(jd, lat, lon)`. Flag Lahiri: `swe.set_sid_mode(swe.SIDM_LAHIRI)`. Timezone: convert to UT first.
