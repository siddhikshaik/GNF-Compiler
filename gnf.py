from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
import re

EPS = "ε"

def unique(seq):
    seen = set()
    out = []
    for x in seq:
        t = tuple(x)
        if t not in seen:
            seen.add(t)
            out.append(list(x))
    return out

def tokenize_rhs(rhs, variables):
    rhs = rhs.strip()
    if not rhs:
        return []
    if rhs in {"ε", "epsilon", "EPS", "eps"}:
        return [EPS]
    if " " in rhs:
        return rhs.split()

    # Prefer known multi-character variables; otherwise treat each character
    # as a symbol. This makes examples such as S -> AB | a convenient.
    ordered = sorted(variables, key=len, reverse=True)
    out, i = [], 0
    while i < len(rhs):
        matched = None
        for v in ordered:
            if rhs.startswith(v, i):
                matched = v
                break
        if matched:
            out.append(matched)
            i += len(matched)
        else:
            out.append(rhs[i])
            i += 1
    return out

def parse(text):
    raw = []
    variables = []
    seen_v = set()
    for line_no, rawline in enumerate(text.splitlines(), 1):
        line = rawline.strip()
        if not line:
            continue
        if "->" not in line:
            raise ValueError(f"Line {line_no}: expected 'A -> ...'")
        lhs, rhs = [p.strip() for p in line.split("->", 1)]
        if not lhs:
            raise ValueError(f"Line {line_no}: empty left-hand side")
        if lhs not in seen_v:
            seen_v.add(lhs)
            variables.append(lhs)
        for alt in rhs.split("|"):
            alt = alt.strip()
            raw.append((lhs, alt))

    if not variables:
        raise ValueError("Enter at least one production.")
    if variables[0] == "":
        raise ValueError("Invalid start symbol.")

    G = {v: [] for v in variables}
    for lhs, rhs in raw:
        G[lhs].append(tokenize_rhs(rhs, variables))
    for v in variables:
        G[v] = unique(G[v])
    return G, variables[0]

def is_epsilon(rhs):
    return rhs == [EPS] or not rhs

def is_unit(rhs, variables):
    return len(rhs) == 1 and rhs[0] in variables

def format_grammar(G, order=None):
    if order is None:
        order = list(G)
    lines = []
    for v in order:
        if v not in G or not G[v]:
            continue
        alts = []
        for rhs in G[v]:
            alts.append(EPS if is_epsilon(rhs) else " ".join(rhs))
        lines.append(f"{v} → " + " | ".join(alts))
    return "\n".join(lines) if lines else "∅"

def clone(G):
    return {a: [list(r) for r in rs] for a, rs in G.items()}

def add(G, lhs, rhs):
    if rhs not in G[lhs]:
        G[lhs].append(list(rhs))

def nullable_set(G):
    nullable = set()
    changed = True
    while changed:
        changed = False
        for A, rules in G.items():
            if A in nullable:
                continue
            for r in rules:
                if is_epsilon(r) or all(x in nullable for x in r):
                    nullable.add(A)
                    changed = True
                    break
    return nullable

def epsilon_eliminate(G, start):
    nullable = nullable_set(G)
    H = {A: [] for A in G}
    for A, rules in G.items():
        for r in rules:
            if is_epsilon(r):
                continue
            positions = [i for i, x in enumerate(r) if x in nullable]
            n = len(positions)
            for mask in range(1 << n):
                removed = {positions[j] for j in range(n) if mask & (1 << j)}
                nr = [x for i, x in enumerate(r) if i not in removed]
                if nr:
                    add(H, A, nr)
                elif A == start:
                    add(H, A, [EPS])
    # Keep start -> ε only if original language can generate epsilon.
    if start in nullable:
        add(H, start, [EPS])
    return H

def unit_eliminate(G):
    vars_ = list(G)
    H = {A: [] for A in vars_}
    for A in vars_:
        closure = {A}
        stack = [A]
        while stack:
            X = stack.pop()
            for r in G[X]:
                if is_unit(r, vars_) and r[0] not in closure:
                    closure.add(r[0])
                    stack.append(r[0])
        for X in closure:
            for r in G[X]:
                if not is_unit(r, vars_):
                    add(H, A, r)
    return H

def productive_set(G):
    vars_ = set(G)
    productive = set()
    changed = True
    while changed:
        changed = False
        for A, rules in G.items():
            if A in productive:
                continue
            for r in rules:
                if is_epsilon(r) or all(x not in vars_ or x in productive for x in r):
                    productive.add(A)
                    changed = True
                    break
    return productive

def reachable_set(G, start):
    vars_ = set(G)
    reachable = {start}
    stack = [start]
    while stack:
        A = stack.pop()
        for r in G.get(A, []):
            for x in r:
                if x in vars_ and x not in reachable:
                    reachable.add(x)
                    stack.append(x)
    return reachable

def remove_useless(G, start):
    productive = productive_set(G)
    H = {A: [] for A in G if A in productive}
    if start not in H:
        return {start: []}
    for A in H:
        for r in G[A]:
            if all(x not in G or x in H for x in r):
                add(H, A, r)
    reachable = reachable_set(H, start)
    return {A: [r for r in H[A] if all(x not in H or x in reachable for x in r)]
            for A in H if A in reachable}

def substitute_first(G, A, B):
    new = []
    for r in G[A]:
        if r and r[0] == B:
            suffix = r[1:]
            for br in G[B]:
                if is_epsilon(br):
                    nr = suffix
                else:
                    nr = br + suffix
                if nr:
                    new.append(nr)
                elif A == B:
                    continue
        else:
            new.append(r)
    G[A] = unique(new)

def eliminate_immediate_left_recursion(G, A, fresh_counter):
    alpha, beta = [], []
    for r in G[A]:
        if r and r[0] == A:
            alpha.append(r[1:])
        else:
            beta.append(r)
    if not alpha:
        return None, fresh_counter

    # A -> beta C ; C -> alpha C | ε
    idx = fresh_counter
    C = f"{A}_R{idx}"
    while C in G:
        idx += 1
        C = f"{A}_R{idx}"
    G[C] = []
    newA = []
    for b in beta:
        if is_epsilon(b):
            newA.append([C])
        else:
            newA.append(b + [C])
    for a in alpha:
        G[C].append(a + [C] if a else [C])
    G[C].append([EPS])
    G[A] = unique(newA)
    G[C] = unique(G[C])
    return C, idx + 1

def eliminate_left_recursion(G, order):
    G = clone(G)
    order = list(order)
    fresh_counter = 1

    i = 0
    while i < len(order):
        Ai = order[i]
        for j in range(i):
            Aj = order[j]
            substitute_first(G, Ai, Aj)
        new_var, fresh_counter = eliminate_immediate_left_recursion(
            G, Ai, fresh_counter
        )
        if new_var:
            # New variable is conceptually after Ai.
            order.append(new_var)
        i += 1
    return G, order

def gnf_substitution(G, order):
    # Ordered substitution: after left-recursion elimination, repeatedly
    # replace a leading variable by its productions until all rules lead
    # with a terminal. Processing variables in order ensures earlier variables
    # have already been expanded.
    G = clone(G)
    vars_set = set(G)

    for i, A in enumerate(order):
        if A not in G:
            continue
        for j in range(i):
            B = order[j]
            new = []
            for r in G[A]:
                if r and r[0] == B:
                    suffix = r[1:]
                    for br in G[B]:
                        if is_epsilon(br):
                            nr = suffix
                        else:
                            nr = br + suffix
                        if nr:
                            new.append(nr)
                else:
                    new.append(r)
            G[A] = unique(new)

    # Some generated helper-variable chains may remain. Resolve them by
    # repeated substitution until stable, with a safety bound.
    changed = True
    rounds = 0
    while changed and rounds < max(10, len(G) * len(G) * 2):
        changed = False
        rounds += 1
        for A in list(G):
            new = []
            for r in G[A]:
                if r and r[0] in vars_set:
                    B = r[0]
                    suffix = r[1:]
                    replacements = G.get(B, [])
                    if replacements:
                        changed = True
                        for br in replacements:
                            nr = (br if not is_epsilon(br) else []) + suffix
                            if nr:
                                new.append(nr)
                    else:
                        new.append(r)
                else:
                    new.append(r)
            G[A] = unique(new)
    return G

def factor_terminals_in_suffix(G, start):
    """Replace terminals occurring after the first RHS symbol by helper variables."""
    H = clone(G)
    terminals = sorted({x for rs in H.values() for r in rs for x in r[1:]
                        if x not in H and x != EPS})
    mapping = {}
    used = set(H)
    for t in terminals:
        base = "T_" + re.sub(r"[^A-Za-z0-9_]", "X", t)
        name = base
        n = 1
        while name in used:
            n += 1
            name = f"{base}{n}"
        used.add(name)
        mapping[t] = name
    for A in list(H):
        new=[]
        for r in H[A]:
            if len(r) <= 1:
                new.append(r)
            else:
                new.append([r[0]] + [mapping.get(x, x) for x in r[1:]])
        H[A]=unique(new)
    for t,name in mapping.items():
        H[name]=[[t]]
    return H

def validate_gnf(G, start):
    vars_ = set(G)
    violations = []
    for A, rules in G.items():
        for r in rules:
            if is_epsilon(r):
                if A != start:
                    violations.append((A, r, "ε is allowed only for the start symbol"))
                continue
            if not r:
                violations.append((A, r, "empty production"))
                continue
            if r[0] in vars_:
                violations.append((A, r, "RHS begins with a variable"))
            if any(x in vars_ is False for x in []):
                pass
            # Every symbol after the first must be a variable.
            for x in r[1:]:
                if x not in vars_:
                    violations.append((A, r, f"symbol '{x}' after the first position is not a variable"))
                    break
    return violations

def analyze_grammar(text):
    G, start = parse(text)
    vars_ = set(G)
    terminals = sorted({x for rs in G.values() for r in rs for x in r
                        if x not in vars_ and x != EPS})
    eps = sum(1 for rs in G.values() for r in rs if is_epsilon(r))
    units = sum(1 for rs in G.values() for r in rs if is_unit(r, vars_))
    left = sum(1 for A, rs in G.items() for r in rs if r and r[0] == A)
    violations = validate_gnf(G, start)
    return {
        "ok": True,
        "start": start,
        "variables": list(G),
        "terminals": terminals,
        "production_count": sum(len(x) for x in G.values()),
        "epsilon_count": eps,
        "unit_count": units,
        "left_recursion_count": left,
        "gnf_violations": len(violations),
        "valid_gnf": len(violations) == 0 and sum(map(len, G.values())) > 0,
        "violations": [{"lhs":a, "rhs": EPS if is_epsilon(r) else " ".join(r), "reason":reason}
                       for a,r,reason in violations]
    }

def convert_to_gnf(text):
    G, start = parse(text)
    order = list(G)
    stages = []

    def snap(name, description, Gx, ordx=None, kind="transform"):
        stages.append({
            "name": name,
            "description": description,
            "grammar": format_grammar(Gx, ordx or list(Gx)),
            "kind": kind,
        })

    snap("Original CFG", "The grammar supplied by the user.", G, order, "input")

    nullable = sorted(nullable_set(G))
    G1 = epsilon_eliminate(G, start)
    snap("Remove ε-productions",
         f"Nullable variables detected: {', '.join(nullable) if nullable else 'none'}. "
         "Nullable occurrences are expanded and ε rules are removed except an allowed start-symbol ε.",
         G1, order)

    G2 = unit_eliminate(G1)
    snap("Remove unit productions",
         "Unit-production closure is expanded so rules of the form A → B are removed.",
         G2, order)

    G3 = remove_useless(G2, start)
    order = [x for x in order if x in G3]
    snap("Remove useless symbols",
         "Non-productive and unreachable variables are removed.",
         G3, order)

    G4, order = eliminate_left_recursion(G3, order)
    snap("Eliminate left recursion",
         "Indirect recursion is substituted using the variable order, then immediate recursion is eliminated with helper variables.",
         G4, order)

    G5 = gnf_substitution(G4, order)
    # Left-recursion elimination can introduce helper epsilon rules. Remove
    # those helper epsilons again, expanding nullable occurrences.
    G5 = epsilon_eliminate(G5, start)
    G5 = gnf_substitution(G5, order)
    G5 = epsilon_eliminate(G5, start)
    G5 = factor_terminals_in_suffix(G5, start)
    snap("Convert to terminal-leading form",
         "Leading variables are substituted, helper ε rules are removed, and terminals after the first position are replaced by terminal-helper variables.",
         G5, list(G5))

    violations = validate_gnf(G5, start)
    snap("GNF validation",
         "Every production is checked against A → aα, with α containing variables only; start → ε is permitted when present.",
         G5, order, "result")

    final_violations = validate_gnf(G5, start)
    final_vars = list(G5)
    final_var_set = set(G5)
    final_terms = sorted({x for rs in G5.values() for r in rs for x in r
                          if x not in final_var_set and x != EPS})
    stats = {
        "ok": True,
        "start": start,
        "variables": final_vars,
        "terminals": final_terms,
        "production_count": sum(len(rs) for rs in G5.values()),
        "epsilon_count": sum(1 for rs in G5.values() for r in rs if is_epsilon(r)),
        "unit_count": sum(1 for rs in G5.values() for r in rs if is_unit(r, final_var_set)),
        "left_recursion_count": sum(1 for A, rs in G5.items() for r in rs if r and r[0] == A),
        "gnf_violations": len(final_violations),
        "valid_gnf": len(final_violations) == 0 and sum(map(len, G5.values())) > 0,
        "violations": [{"lhs":a, "rhs": EPS if is_epsilon(r) else " ".join(r), "reason":reason}
                       for a,r,reason in final_violations]
    }
    return {
        "ok": True,
        "start": start,
        "stages": stages,
        "result": stats,
        "complete_gnf": stats["valid_gnf"],
        "error": None
    }
