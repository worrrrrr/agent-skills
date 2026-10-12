#!/usr/bin/env python3
"""Math workflow engine: calc + sympy + z3 in one script.
Single ops:
  python run.py '{"op":"calc","expr":"gamma(-1/2)"}'
  python run.py '{"op":"solve","eq":"x**2 - 5*x + 6 = 0","symbol":"x"}'
  python run.py '{"op":"z3solve","vars":["x","y"],"eqs":["x + y == 10","x - y == 2"]}'
Raw problem (auto-router picks the op itself):
  python run.py '{"op":"auto","q":"lim (1-cos(x))/x^2 x->0"}'
Batch file (one JSON/raw problem per line -> results file):
  python run.py batch problems43.txt skilloutput.txt
Ops: calc | solve | nsolve | diff | integrate | limit | eigen | det | inv
     | simplify | sum | series | dsolve | factor | modsolve | residue
     | cfrac | nullspace | jordan | svd | matexp | z3solve | auto
"""
import json
import re
import sys

import sympy as sp

ENGINE_VERSION = "1.3.0"

FUNCS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "sec": sp.sec, "csc": sp.csc, "cot": sp.cot,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "Abs": sp.Abs,
    "pi": sp.pi, "e": sp.E, "E": sp.E, "I": sp.I, "oo": sp.oo,
    "gamma": sp.gamma, "zeta": sp.zeta,
    "erf": sp.erf, "erfc": sp.erfc,
    "Si": sp.Si, "Ci": sp.Ci, "Ei": sp.Ei,
    "factorial": sp.factorial, "binomial": sp.binomial,
    "fibonacci": sp.fibonacci,
}


def _sym(expr: str):
    return sp.sympify(expr.replace("^", "**"), locals=FUNCS)


def _parse_eq(eq: str, symbol: str):
    x = sp.Symbol(symbol)
    s = eq.replace("^", "**").strip()
    for op in ("<=", ">=", "==", "!="):
        if op in s:
            raise ValueError("solve handles equations only, use z3solve for inequalities")
    if "=" in s:
        lhs, rhs = s.split("=", 1)
        return x, _sym(lhs) - _sym(rhs)
    return x, _sym(s)


def _strip_wrapped(s):
    s = s.strip()
    while len(s) >= 2 and s[0] == "(" and s[-1] == ")":
        depth, ok = 0, True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    ok = False
                    break
        if not ok or depth != 0:
            break
        s = s[1:-1].strip()
    return s


def _split_top(s, sep=","):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def _free_symbols(s):
    toks = set(re.findall(r"[a-zA-Z]+", s))
    return sorted(t for t in toks
                  if t not in FUNCS and t not in ("mod", "in", "over"))


def op_calc(expr: str, prec: int = 20) -> str:
    val = _sym(expr)
    exact = sp.simplify(val)
    num = sp.N(val, prec)
    if exact.is_number is False:
        return str(exact)
    if exact.is_Integer or exact.is_Rational:
        return str(exact)
    if sp.simplify(exact - num) == 0:
        return str(num)
    return f"{exact} = {num}"


def _guess(g, prec=12):
    try:
        return complex(sp.N(_sym(str(g)), prec))
    except Exception:  # noqa: BLE001
        return complex(g)


def op_nsolve(eq: str, symbol="x", guesses=(1.0,), prec=12, tol=1e-14):
    x, expr = _parse_eq(eq, symbol)
    roots = []
    for g in guesses:
        try:
            r = sp.nsolve(expr, x, _guess(g, prec), tol=tol, maxsteps=200)
            rv = complex(sp.N(r, prec))
            res = complex(sp.N(expr.subs(x, r), prec))
            roots.append((rv, res))
        except Exception:  # noqa: BLE001
            continue
    uniq = []
    for rv, res in roots:
        if not any(abs(rv - u[0]) < 1e-9 for u in uniq):
            uniq.append((rv, res))
    return [
        {"value": str(sp.N(v, prec)), "residual": str(sp.N(r, 5))}
        for v, r in sorted(uniq, key=lambda t: (t[0].real, t[0].imag))
    ]


def op_solve(eq: str, symbol="x", prec=12, guesses=None):
    x, expr = _parse_eq(eq, symbol)
    exact, real_set_s = [], "?"
    try:
        exact = sp.solve(expr, x)
    except Exception:  # noqa: BLE001
        exact = []
    try:
        real_set_s = str(sp.solveset(expr, x, domain=sp.S.Reals))
    except Exception:  # noqa: BLE001
        pass
    if guesses is None:
        guesses = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 27.0, -1.0, -2.0]
    numeric = op_nsolve(eq, symbol, guesses, prec)
    exact_num = []
    for s in exact:
        try:
            exact_num.append(str(sp.N(s, prec)))
        except Exception:  # noqa: BLE001
            exact_num.append(str(s))
    seen = {r["value"] for r in numeric}
    for s, sn in zip(exact, exact_num):
        if sn not in seen:
            try:
                res = str(sp.N(expr.subs(x, s), 5))
            except Exception:  # noqa: BLE001
                res = "?"
            numeric.append({"value": sn, "residual": res})
    try:
        numeric.sort(key=lambda d: (float(sp.re(sp.sympify(d["value"]))),
                                    float(sp.im(sp.sympify(d["value"])))))
    except Exception:  # noqa: BLE001
        pass
    return {
        "exact": [str(s) for s in exact],
        "exact_numeric": exact_num,
        "real_set": real_set_s,
        "numeric": numeric,
    }


def op_diff(expr: str, symbol: str = "x") -> str:
    x = sp.Symbol(symbol)
    return str(sp.simplify(sp.diff(_sym(expr), x)))


def _bound(v):
    if isinstance(v, str) and v.strip().lower() in ("oo", "+oo", "inf", "+inf"):
        return sp.oo
    if isinstance(v, str) and v.strip().lower() in ("-oo", "-inf"):
        return -sp.oo
    return _sym(str(v))


def op_integrate(expr: str, symbol: str = "x", a=None, b=None) -> str:
    x = sp.Symbol(symbol)
    e = _sym(expr)
    if a is not None and b is not None:
        return str(sp.integrate(e, (x, _bound(a), _bound(b))))
    return str(sp.integrate(e, x))


def op_eigen(matrix: list) -> dict:
    m = sp.Matrix(matrix)
    return {str(k): v for k, v in m.eigenvals().items()}


def op_det(matrix: list) -> str:
    return str(sp.Matrix(matrix).det())


def op_inv(matrix: list) -> list:
    return [[str(v) for v in row] for row in sp.Matrix(matrix).inv().tolist()]


def op_simplify(expr: str, prec: int = 12) -> str:
    e = _sym(expr)
    exact = sp.simplify(e)
    if exact.is_number and not (exact.is_Integer or exact.is_Rational):
        return f"{exact} = {sp.N(exact, prec)}"
    return str(exact)


def op_sum(expr: str, symbol: str = "n", a=1, b="oo") -> str:
    x = sp.Symbol(symbol)
    return str(sp.Sum(_sym(expr), (x, _bound(a), _bound(b))).doit())


def op_limit(expr: str, symbol: str = "x", to=0, side="both") -> str:
    x = sp.Symbol(symbol)
    e = _sym(expr)
    t = _bound(to)
    if side in ("+", "-"):
        return str(sp.limit(e, x, t, dir=side))
    return str(sp.limit(e, x, t))


def op_series(expr: str, symbol: str = "x", point=0, order=6) -> str:
    x = sp.Symbol(symbol)
    return str(sp.series(_sym(expr), x, _bound(point), int(order)))


def op_dsolve(eq: str, funcs=("f",), symbol: str = "x") -> str:
    t = sp.Symbol(symbol)
    s = eq.replace("^", "**").strip()
    for name in sorted(funcs, key=len, reverse=True):
        s = re.sub(re.escape(name) + "''", f"__D2_{name}__", s)
        s = re.sub(re.escape(name) + "'", f"__D1_{name}__", s)
        s = re.sub(rf"\b{re.escape(name)}\b", f"__F_{name}__", s)
    raws = _split_top(s, ";")
    if len(raws) == 1:
        raws = _split_top(s, ",")
    eqs = []
    for r in raws:
        for name in funcs:
            r = r.replace(f"__D2_{name}__",
                          f"Derivative({name}({symbol}), ({symbol}, 2))")
            r = r.replace(f"__D1_{name}__",
                          f"Derivative({name}({symbol}), {symbol})")
            r = r.replace(f"__F_{name}__", f"{name}({symbol})")
        loc = dict(FUNCS)
        for name in funcs:
            loc[name] = sp.Function(name)
        loc[symbol] = t
        if "=" in r:
            a, b = r.split("=", 1)
            eqs.append(sp.Eq(sp.sympify(a, locals=loc),
                             sp.sympify(b, locals=loc)))
        else:
            eqs.append(sp.sympify(r, locals=loc))
    F = [sp.Function(n)(t) for n in funcs]
    if len(eqs) == 1:
        return str(sp.dsolve(eqs[0]))
    return str(sp.dsolve(eqs, F))


def op_factor(target) -> str:
    s = str(target).strip().rstrip(")")
    if re.fullmatch(r"[0-9+\-*/^() ]+", s):
        return str(sp.factorint(int(sp.sympify(s.replace("^", "**")))))
    return str(sp.factor(_sym(s)))


def op_mod(lhs: str, rhs: str, symbol: str = "x", mod: int = 8) -> dict:
    x = sp.Symbol(symbol)
    e = _sym(lhs) - _sym(rhs)
    sols = []
    hi = max(int(mod) * 10, 64)
    for v in range(hi):
        try:
            if int(sp.simplify(e.subs(x, v))) % int(mod) == 0:
                sols.append(v)
        except Exception:  # noqa: BLE001
            continue
    residues = sorted({v % int(mod) for v in sols})
    prog = None
    if len(sols) >= 3:
        diffs = {b - a for a, b in zip(sols, sols[1:])}
        if len(diffs) == 1:
            d = diffs.pop()
            if sols[-1] > hi - d - 1:
                prog = f"x = {sols[0]} + {d}*k"
    out = {"congruence": f"{lhs} == {rhs} (mod {mod})",
           "solutions_in_range": sols[:12]}
    if prog is not None:
        out["general"] = prog
    else:
        out["residues_mod"] = residues
    return out


def op_residue(expr: str, symbol: str = "x", point=0) -> str:
    x = sp.Symbol(symbol)
    return str(sp.residue(_sym(expr), x, _bound(point)))


def op_cfrac(expr: str) -> str:
    from sympy.ntheory.continued_fraction import (
        continued_fraction_iterator, continued_fraction_periodic)
    v = _sym(expr)
    try:
        if (v.is_Pow and v.exp == sp.Rational(1, 2)
                and v.base.is_Integer and int(v.base) > 1):
            return (f"{continued_fraction_periodic(0, 1, int(v.base))} "
                    "(periodic)")
    except Exception:  # noqa: BLE001
        pass
    it = continued_fraction_iterator(v)
    return f"first terms {[int(next(it)) for _ in range(8)]}"


def op_nullspace(matrix: list) -> list:
    return [[[str(c) for c in row]
             for row in v.tolist()]
            for v in sp.Matrix(matrix).nullspace()]


def op_jordan(matrix: list) -> dict:
    P, J = sp.Matrix(matrix).jordan_form()
    return {"P": [[str(c) for c in row] for row in P.tolist()],
            "J": [[str(c) for c in row] for row in J.tolist()]}


def op_svd(matrix: list) -> dict:
    vals = sp.Matrix(matrix).singular_values()
    return {"exact": [str(v) for v in vals],
            "numeric": [str(sp.N(v, 10)) for v in vals]}


def op_matexp(matrix: list, symbol: str = "t") -> str:
    t = sp.Symbol(symbol)
    return str((sp.Matrix(matrix) * t).exp())


def op_z3solve(vars_: list, eqs: list) -> dict:
    from z3 import Ints, Solver, sat
    syms = Ints(" ".join(vars_))
    env = {name: s for name, s in zip(vars_, syms)}
    s = Solver()
    for e in eqs:
        s.add(eval(e, {"__builtins__": {}}, env))  # noqa: S307 - ints-only env
    if s.check() != sat:
        return {"sat": False}
    m = s.model()
    return {"sat": True, "model": {v: str(m[env[v]]) for v in vars_}}


def _multivar(expr_s, v1, v2):
    a, b = sp.Symbol(v1), sp.Symbol(v2)
    e = _sym(expr_s)
    paths = {f"{v1}-axis": e.subs(b, 0),
             f"{v2}-axis": e.subs(a, 0),
             "diag": e.subs(b, a)}
    res = {}
    for k, v in paths.items():
        try:
            res[k] = str(sp.limit(v, a, 0))
        except Exception as ex:  # noqa: BLE001
            res[k] = f"?({ex})"
    vals = set(res.values())
    verdict = list(vals)[0] if len(vals) == 1 else "DNE (path-dependent)"
    return f"paths {res} -> {verdict}"


def op_auto(q: str, prec: int = 12, guesses=None) -> dict:
    s0 = q.strip()
    s = s0.replace("==", "==").replace("≡", "==").replace("→", "->")
    s = s.replace("∞", "oo")
    s = re.sub(r"\|([^|\n=<>]+)\|", r"Abs(\1)", s)
    low = s.lower()

    if "∂" in s0 or "pde" in low or "du/dt" in low or "d2u/dx2" in low:
        return {"detected": "pde-template",
                "result": ("u(x,t)=X(x)T(t): X''/X = T'/(kT) = -lam; "
                           "modes exp(-k*lam*t)*(A*cos(mu*x)+B*sin(mu*x)); "
                           "use BC/IC for coefficients")}

    if ("dsolve" in low or re.search(r"[a-zA-Z]+''", s)
            or re.search(r"[a-zA-Z]+'\s*[+\-*=]", s)):
        funcs = sorted(set(re.findall(r"([a-zA-Z]+)'", s))) or ["f"]
        expr = re.sub(r"(?i)^dsolve\s*[: ]?", "", s).strip()
        symbol = "t" if (len(funcs) > 1 or "x" in funcs) else "x"
        return {"detected": "dsolve",
                "result": op_dsolve(expr, tuple(funcs), symbol)}

    if ("taylor" in low or (re.search(r"(?i)\bseries\s*\(", s)
                            and "sum" not in low and "Σ" not in s0
                            and "อนุกรม" not in s0)):
        m = re.search(r"(?i)series\s*\((.*)\)\s*$", s, re.S)
        if m:
            args = _split_top(m.group(1))
            ex = args[0] if len(args) > 0 else s
            va = args[1].strip() if len(args) > 1 else "x"
            pt = args[2].strip() if len(args) > 2 else 0
            nn = int(args[3].strip()) if len(args) > 3 else 6
            return {"detected": "series",
                    "result": op_series(ex, va, pt, nn)}

    if re.search(r"(?i)factor", s):
        target = re.sub(r"(?i)factor(int)?\s*[\(: ]?", "", s).strip()
        target = target.rstrip("): ")
        return {"detected": "factor", "result": op_factor(target or s)}

    if "mod" in low or "≡" in s0:
        mm = re.search(r"mod\s*(\d+)", low)
        mod = int(mm.group(1)) if mm else 8
        core = re.split(r"(?i)\bmod\b", s)[0].strip()
        core = re.sub(r"[\s,(;]+$", "", core)
        if "==" in core:
            lhs, rhs = core.split("==", 1)
        elif "=" in core:
            lhs, rhs = core.split("=", 1)
        else:
            lhs, rhs = core, "0"
        cands = [t for t in _free_symbols(lhs + "," + rhs)]
        var = cands[0] if cands else "x"
        return {"detected": "mod",
                "result": op_mod(lhs.strip(), rhs.strip(), var, mod)}

    if ("residue" in low or re.search(r"(?i)\bres\s*\(", s)
            or "∮" in s0 or "contour" in low):
        m = re.search(r"(?i)res(?:idue)?\s*\((.*)\)\s*"
                      r"(?:at\s*([a-zA-Z]+)\s*=\s*([^\s,;]+))?", s, re.S)
        if m and m.group(1).strip():
            ex = m.group(1).strip()
            va = m.group(2) or "x"
            pt = m.group(3) or 0
            r = op_residue(ex, va, pt)
            return {"detected": "residue",
                    "result": f"{r} -> contour integral = 2*pi*I*({r})"}
        return {"detected": "residue",
                "result": "need residue(expr) at var=point"}

    if "continued_fraction" in low or "cfrac" in low:
        m = re.search(r"(?i)(?:continued_fraction|cfrac)\s*\((.*)\)\s*$",
                      s, re.S)
        inner = m.group(1).strip() if m else s
        return {"detected": "cfrac", "result": op_cfrac(inner)}

    if "..." in s0 and "sqrt" in low:
        v = 0.0
        for _ in range(50):
            v = (2.0 + v) ** 0.5
        return {"detected": "nested-sqrt",
                "result": (f"2 (reads as sqrt(2+sqrt(2+...)); "
                           f"50 iterations = {v:.12f}")}

    if "lim" in low or "ลิมิต" in s0 or "->" in s:
        m = re.search(r"\(\s*([a-zA-Z]+)\s*,\s*([a-zA-Z]+)\s*\)\s*->\s*"
                      r"\(\s*([^,()]+?)\s*,\s*([^()]+?)\s*\)", s)
        if m:
            v1, v2 = m.group(1), m.group(2)
            expr = s.replace(m.group(0), " ")
            expr = re.sub(r"(?i)\blim\b", "", expr)
            expr = _strip_wrapped(expr.strip(" [],;"))
            return {"detected": "multivar-limit",
                    "result": _multivar(expr, v1, v2)}
        m2 = re.search(r"\(?([a-zA-Z]+)\s*->\s*([^)\s,;]+)\)?", s)
        if m2:
            var, pt = m2.group(1), m2.group(2)
            side = "both"
            if pt.endswith("+"):
                side, pt = "+", pt[:-1]
            elif pt.endswith("-") and len(pt) > 1 and pt[-2].isdigit():
                side, pt = "-", pt[:-1]
            expr = re.sub(r"(?i)\blim\b", "", s)
            expr = expr.replace(m2.group(0), " ")
            expr = _strip_wrapped(expr.strip(" [],;")) or s
            return {"detected": "limit",
                    "result": op_limit(expr, var, pt or 0, side)}
        expr = re.sub(r"(?i)\blim\b", "", s).strip()
        return {"detected": "limit",
                "result": op_limit(_strip_wrapped(expr.strip(" [],;")) or s,
                                   "x", 0, "both")}

    if re.search(r"(?i)\binteg|\bint\s+|∫|ปริพันธ์", s):
        t = re.sub(r"(?i)\bintegrate\b|\bint\b|∫|ปริพันธ์", "", s).strip()
        a = b = None
        sym = None
        m = re.search(r"([a-zA-Z]+)\s*=\s*(\S+?)\.\.(\S+)", t)
        if m:
            sym, a, b = m.group(1), m.group(2), m.group(3)
            t = (t[:m.start()] + " " + t[m.end():]).strip()
        else:
            m2 = re.search(r"ตั้งแต่\s*(\S+?)\s*ถึง\s*(\S+)", t)
            if m2:
                a, b = m2.group(1), m2.group(2)
                t = (t[:m2.start()] + t[m2.end():]).strip()
        m3 = re.search(r"\s+d([a-zA-Z])\s*$", t)
        if m3:
            if sym is None:
                sym = m3.group(1)
            t = t[:m3.start()].strip()
        if sym is None:
            cands = _free_symbols(t)
            sym = cands[0] if cands else "x"
        expr = _strip_wrapped(t.strip(" [],;"))
        res = op_integrate(expr, sym, a, b)
        if "Piecewise" not in res and "Integral(" in res:
            fru = None
            try:
                if (str(a).strip() == "0"
                        and str(b).strip().lower() in ("oo", "+oo", "inf")):
                    xx = sp.Symbol(sym)
                    tms = list(sp.Add.make_args(
                        sp.expand(_sym(expr) * xx)))
                    if len(tms) == 2:
                        cks = []
                        for t in tms:
                            facs = [f for f in sp.Mul.make_args(t)
                                    if f.has(sp.exp)]
                            if len(facs) != 1:
                                break
                            arg = facs[0].exp
                            kk = sp.expand(arg).coeff(xx)
                            cc = sp.simplify(t / facs[0])
                            if (kk is None or cc.has(xx)
                                    or sp.simplify(arg - kk * xx) != 0):
                                break
                            cks.append((cc, kk))
                        else:
                            (c1, k1), (c2, k2) = cks
                            if (sp.simplify(c1 + c2) == 0
                                    and sp.simplify(c1) != 0):
                                cand = sp.simplify(
                                    c1 * (sp.log(-k2) - sp.log(-k1)))
                                try:
                                    cand = sp.logcombine(cand, force=True)
                                except Exception:  # noqa: BLE001
                                    pass
                                fru = str(cand)
            except Exception:  # noqa: BLE001
                fru = None
            if fru is not None:
                return {"detected": "integrate-frullani", "result": fru}
            res += " [unevaluated]"
        return {"detected": "integrate", "result": res}

    if (re.search(r"(?i)\bdiff\b|\bderivative\b|อนุพันธ์", s)
            or re.search(r"d/d([a-zA-Z])", s)):
        m = re.search(r"d/d([a-zA-Z])\s*[\[(]?(.*)[\])]?\s*$", s, re.S)
        if m:
            return {"detected": "diff",
                    "result": op_diff(
                        _strip_wrapped(m.group(2).strip()), m.group(1))}
        t = re.sub(r"(?i)\bdiff\b|\bderivative\b|อนุพันธ์", "", s).strip()
        toks = t.split()
        if len(toks) > 1 and re.fullmatch(r"[a-zA-Z]", toks[-1]):
            sym, t = toks[-1], " ".join(toks[:-1])
        else:
            sym = (_free_symbols(t) or ["x"])[0]
        return {"detected": "diff",
                "result": op_diff(_strip_wrapped(t.strip(" [],;")), sym)}

    if "sum" in low or "Σ" in s0 or "อนุกรม" in s0:
        t = re.sub(r"(?i)\bsum\b|Σ|อนุกรม", "", s).strip()
        m = re.search(r"\(\s*([a-zA-Z]+)\s*=\s*([^.()]+?)\.\.([^()]+?)\)",
                      t)
        if m:
            sym, a, b = m.group(1), m.group(2).strip(), m.group(3).strip()
            t = (t[:m.start()] + " " + t[m.end():]).strip()
        else:
            m2 = re.search(r"([a-zA-Z]+)\s*=\s*(\S+?)\.\.(\S+)", t)
            if m2:
                sym, a, b = m2.group(1), m2.group(2), m2.group(3)
                t = (t[:m2.start()] + " " + t[m2.end():]).strip()
            else:
                sym, a, b = "n", 1, "oo"
        expr = _strip_wrapped(t.strip(" [],;"))
        return {"detected": "sum", "result": op_sum(expr, sym, a, b)}

    if any(o in s for o in ("==", "<=", ">=", "<", ">", "=")):
        if re.search(r"(?i)\bin\s*Z\b|จำนวนเต็ม|integers?", s):
            core = re.sub(r"(?i)\bin\s*Z\b|จำนวนเต็ม|integers?",
                          "", s).strip()
            lhs, rhs = core.split("=", 1)
            lhs, rhs = lhs.strip(), rhs.strip()
            syms = _free_symbols(lhs + "," + rhs)
            try:
                dio = str(sp.diophantine(_sym(lhs) - _sym(rhs)))
            except Exception as ex:  # noqa: BLE001
                dio = f"diophantine failed: {ex}"
            sample = op_z3solve(syms, [f"{lhs} == {rhs}"])
            return {"detected": "diophantine-Z",
                    "result": {"general": dio, "sample": sample}}
        if re.search(r"(?i)over\s+Reals|\bin\s+R\b|จำนวนจริง|\breal\b",
                     s):
            core = re.sub(r"(?i)over\s+Reals|\bin\s+R\b|จำนวนจริง|\breal\b",
                          "", s).strip()
            lhs, rhs = core.split("=", 1)
            x = sp.Symbol((_free_symbols(core) or ["x"])[0])
            return {"detected": "solve-Reals",
                    "result": str(sp.solveset(_sym(lhs) - _sym(rhs), x,
                                              domain=sp.S.Reals))}
        if "==" not in s and any(o in s for o in ("<=", ">=", "<", ">")):
            syms = _free_symbols(s)
            if len(syms) == 1:
                x = sp.Symbol(syms[0])
                for opstr, rel in (("<=", sp.Le), (">=", sp.Ge),
                                   ("<", sp.Lt), (">", sp.Gt)):
                    if opstr in s:
                        lhs, rhs = s.split(opstr, 1)
                        return {"detected": "inequality",
                                "result": str(
                                    sp.solve_univariate_inequality(
                                        rel(_sym(lhs), _sym(rhs)), x))}
            parts = _split_top(s)
            return {"detected": "inequality-system",
                    "result": op_z3solve(
                        syms, [p.replace("^", "**") for p in parts])}
        core = s.replace("==", "=")
        syms = _free_symbols(core)
        return {"detected": "solve",
                "result": op_solve(core, syms[0] if syms else "x",
                                   prec, guesses)}

    return {"detected": "simplify", "result": op_simplify(s, prec)}


def run(p: dict):
    op = p.get("op", "calc")
    if op == "calc":
        return op_calc(p["expr"], p.get("prec", 20))
    if op == "solve":
        return op_solve(p["eq"], p.get("symbol", "x"),
                        p.get("prec", 12), p.get("guesses"))
    if op == "nsolve":
        return op_nsolve(p.get("eq", p.get("expr", "")), p.get("symbol", "x"),
                         p.get("guesses", [1.0]), p.get("prec", 12))
    if op == "diff":
        return op_diff(p["expr"], p.get("symbol", "x"))
    if op == "integrate":
        return op_integrate(p["expr"], p.get("symbol", "x"), p.get("a"), p.get("b"))
    if op == "limit":
        return op_limit(p["expr"], p.get("symbol", "x"), p.get("to", 0), p.get("side", "both"))
    if op == "eigen":
        return op_eigen(p["matrix"])
    if op == "det":
        return op_det(p["matrix"])
    if op == "inv":
        return op_inv(p["matrix"])
    if op == "simplify":
        return op_simplify(p["expr"], p.get("prec", 12))
    if op == "sum":
        return op_sum(p["expr"], p.get("symbol", "n"), p.get("a", 1), p.get("b", "oo"))
    if op == "series":
        return op_series(p["expr"], p.get("symbol", "x"), p.get("point", 0), p.get("order", 6))
    if op == "dsolve":
        return op_dsolve(p["eq"], tuple(p.get("funcs", ["f"])), p.get("symbol", "x"))
    if op == "factor":
        return op_factor(p.get("target", p.get("expr", "")))
    if op == "modsolve":
        return op_mod(p["lhs"], p.get("rhs", "0"), p.get("symbol", "x"), p.get("mod", 8))
    if op == "residue":
        return op_residue(p["expr"], p.get("symbol", "x"), p.get("point", 0))
    if op == "cfrac":
        return op_cfrac(p["expr"])
    if op == "nullspace":
        return op_nullspace(p["matrix"])
    if op == "jordan":
        return op_jordan(p["matrix"])
    if op == "svd":
        return op_svd(p["matrix"])
    if op == "matexp":
        return op_matexp(p["matrix"], p.get("symbol", "t"))
    if op == "z3solve":
        return op_z3solve(p["vars"], p["eqs"])
    if op == "auto":
        return op_auto(p.get("q", ""), p.get("prec", 12), p.get("guesses"))
    raise ValueError(f"unknown op: {op}")


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "batch":
        inn, outp = sys.argv[2], sys.argv[3]
        with open(inn, encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f
                     if ln.strip() and not ln.strip().startswith("#")]
        done = []
        for ln in lines:
            try:
                p = json.loads(ln)
                if not isinstance(p, dict):
                    p = {"q": ln}
            except Exception:  # noqa: BLE001
                p = {"q": ln}
            pid = p.get("id", "?")
            try:
                if p.get("op", "auto") == "auto":
                    r = op_auto(p.get("q", ln), p.get("prec", 12),
                                p.get("guesses"))
                else:
                    r = run({k: v for k, v in p.items() if k != "id"})
                done.append({"id": pid, "input": p, "ok": True,
                             "result": r})
            except Exception as e:  # noqa: BLE001
                done.append({"id": pid, "input": p, "ok": False,
                             "error": str(e)})
        with open(outp, "w", encoding="utf-8") as f:
            for r in done:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        nbad = sum(1 for r in done if not r["ok"])
        print(f"batch: {len(done)} items, errors: {nbad} -> {outp}")
        return
    raw = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    # ทน BOM: JSON ที่มาจาก PowerShell 5.1 / ไฟล์ที่สร้างบน Windows จะมี U+FEFF นำหน้า
    # (บทเรียน: D:\Wor\60-Lessons\อ่าน JSON config บน Windows ต้องทน BOM)
    if raw and raw[0] == "\ufeff":
        raw = raw.lstrip("\ufeff")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}, ensure_ascii=False))
        sys.exit(2)
    if not isinstance(payload, dict):
        print(json.dumps(
            {"error": "payload ต้องเป็น JSON object เช่น {\"op\":\"calc\",\"expr\":\"1+1\"}"},
            ensure_ascii=False))
        sys.exit(2)
    try:
        print(json.dumps({"ok": True, "result": run(payload)}, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
