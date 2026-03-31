"""
cnf_converter.py - Chomsky Normal Form Converter
==================================================
This module converts a Context-Free Grammar (CFG) into
Chomsky Normal Form (CNF).

CNF Rules:
    1. Every production is of the form:
       A -> BC   (two non-terminals)
       A -> a    (single terminal)
    2. The start symbol does not appear on the right side of any production.
    3. Epsilon (ε) is only allowed for the start symbol (if ε ∈ L).

Conversion Steps:
    Step 1: Add a new start symbol S₀ -> S
    Step 2: Remove ε-productions (nullable non-terminals)
    Step 3: Remove unit productions (A -> B)
    Step 4: Replace terminals in mixed productions with new non-terminals
    Step 5: Break long productions (|body| > 2) into binary productions
"""

import copy
from itertools import product as itertools_product


def convert_to_cnf(productions, start_symbol, non_terminals, terminals):
    """
    Convert a CFG to Chomsky Normal Form (CNF).

    Args:
        productions (dict): Original productions {NT: [[symbols], ...]}
        start_symbol (str): The start symbol
        non_terminals (set): Set of non-terminal symbols
        terminals (set): Set of terminal symbols

    Returns:
        tuple: (cnf_productions, new_start, new_non_terminals, new_terminals, steps_log)
            - cnf_productions: dict in CNF
            - new_start: new start symbol
            - new_non_terminals: updated non-terminals set
            - new_terminals: updated terminals set
            - steps_log: list of (step_name, description, grammar_snapshot) for visualization
    """
    # Deep copy to avoid modifying originals
    prods = copy.deepcopy(productions)
    nts = set(non_terminals)
    terms = set(terminals)
    start = start_symbol
    steps_log = []

    # Record initial state
    steps_log.append(("Original Grammar", "The input grammar before any transformation.", _snapshot(prods, start)))

    # ===== STEP 1: New Start Symbol =====
    start, prods, nts = _step1_new_start(prods, start, nts)
    steps_log.append(("Step 1: New Start Symbol",
                       f"Added new start symbol '{start}' → {start_symbol} to ensure "
                       "the start symbol doesn't appear on the RHS of any production.",
                       _snapshot(prods, start)))

    # ===== STEP 2: Remove ε-productions =====
    prods, nts = _step2_remove_epsilon(prods, start, nts)
    steps_log.append(("Step 2: Remove ε-productions",
                       "Identified nullable non-terminals and removed ε-productions, "
                       "adding new productions to cover all combinations.",
                       _snapshot(prods, start)))

    # ===== STEP 3: Remove Unit Productions =====
    prods = _step3_remove_unit(prods, nts)
    steps_log.append(("Step 3: Remove Unit Productions",
                       "Replaced unit productions (A → B) by substituting "
                       "the productions of B directly.",
                       _snapshot(prods, start)))

    # ===== STEP 4: Replace Terminals in Mixed Bodies =====
    prods, nts, terms = _step4_replace_terminals(prods, nts, terms)
    steps_log.append(("Step 4: Replace Terminals in Long Bodies",
                       "For productions with body length ≥ 2, replaced each terminal 'a' "
                       "with a new non-terminal T_a → a.",
                       _snapshot(prods, start)))

    # ===== STEP 5: Break Long Productions =====
    prods, nts = _step5_break_long(prods, nts)
    steps_log.append(("Step 5: Break Long Productions",
                       "Broke productions with body length > 2 into chains of "
                       "binary productions using new non-terminals.",
                       _snapshot(prods, start)))

    return prods, start, nts, terms, steps_log


# ==================== STEP 1 ====================
def _step1_new_start(prods, start, nts):
    """
    Add a new start symbol S₀ that produces the old start symbol.
    This ensures the start symbol never appears on any RHS.
    """
    new_start = start + "₀"
    # Make sure the new name doesn't collide
    while new_start in nts:
        new_start += "'"

    prods[new_start] = [[start]]
    nts.add(new_start)

    return new_start, prods, nts


# ==================== STEP 2 ====================
def _step2_remove_epsilon(prods, start, nts):
    """
    Remove ε-productions by:
    1. Finding all nullable non-terminals (those that can derive ε)
    2. For each production containing a nullable NT, add versions
       with that NT removed
    3. Remove all ε-productions (except possibly for the start)
    """
    # ---- Find all nullable non-terminals ----
    nullable = set()

    # Direct nullable: A -> ε
    for nt in prods:
        for body in prods[nt]:
            if not body:  # Empty body = epsilon
                nullable.add(nt)

    # Transitive nullable: A -> BCD where B, C, D are all nullable
    changed = True
    while changed:
        changed = False
        for nt in prods:
            if nt in nullable:
                continue
            for body in prods[nt]:
                if body and all(sym in nullable for sym in body):
                    nullable.add(nt)
                    changed = True
                    break

    if not nullable:
        return prods, nts

    # ---- Generate new productions ----
    new_prods = {}
    for nt in prods:
        new_bodies = set()
        for body in prods[nt]:
            if not body:
                continue  # Skip epsilon productions for now

            # Find indices of nullable symbols in this body
            nullable_indices = [i for i, sym in enumerate(body) if sym in nullable]

            # Generate all combinations of including/excluding nullable symbols
            for r in range(len(nullable_indices) + 1):
                for combo in _combinations(nullable_indices, r):
                    # Create new body with selected nullable symbols removed
                    new_body = [sym for i, sym in enumerate(body) if i not in combo]
                    if new_body:  # Don't add empty productions
                        new_bodies.add(tuple(new_body))

        new_prods[nt] = [list(b) for b in new_bodies]

    # If the start symbol was nullable, allow ε for start
    if start in nullable or any(s in nullable for s in [start]):
        # Check if the original start can derive epsilon
        original_start = None
        for body in prods.get(start, []):
            if len(body) == 1 and body[0] in nullable:
                original_start = body[0]
                break
        if start in nullable or (original_start and original_start in nullable):
            if start not in new_prods:
                new_prods[start] = []
            new_prods[start].append([])  # Add ε to new start

    return new_prods, nts


def _combinations(lst, r):
    """Generate all combinations of r elements from lst."""
    if r == 0:
        yield set()
        return
    for i in range(len(lst)):
        for rest in _combinations(lst[i+1:], r - 1):
            yield {lst[i]} | rest


# ==================== STEP 3 ====================
def _step3_remove_unit(prods, nts):
    """
    Remove unit productions (A -> B where B is a single non-terminal).
    For each unit production A -> B, add all non-unit productions of B to A.
    """
    # ---- Find unit pairs using transitive closure ----
    unit_pairs = set()

    for nt in nts:
        # Every NT is in a unit pair with itself
        unit_pairs.add((nt, nt))

    changed = True
    while changed:
        changed = False
        new_pairs = set()
        for (a, b) in unit_pairs:
            for body in prods.get(b, []):
                if len(body) == 1 and body[0] in nts:
                    pair = (a, body[0])
                    if pair not in unit_pairs:
                        new_pairs.add(pair)
                        changed = True
        unit_pairs |= new_pairs

    # ---- Build new productions ----
    new_prods = {}
    for nt in prods:
        new_prods[nt] = []

    for (a, b) in unit_pairs:
        for body in prods.get(b, []):
            # Skip unit productions
            if len(body) == 1 and body[0] in nts:
                continue
            if a not in new_prods:
                new_prods[a] = []
            # Avoid duplicates
            if body not in new_prods[a]:
                new_prods[a].append(body)

    return new_prods


# ==================== STEP 4 ====================
def _step4_replace_terminals(prods, nts, terms):
    """
    For productions with body length ≥ 2, replace each terminal
    with a new non-terminal that produces just that terminal.
    e.g., A -> aBc becomes A -> T_a B T_c, with T_a -> a, T_c -> c
    """
    terminal_map = {}  # terminal -> new non-terminal name

    new_prods = copy.deepcopy(prods)

    for nt in list(new_prods.keys()):
        new_bodies = []
        for body in new_prods[nt]:
            if len(body) < 2:
                new_bodies.append(body)
                continue

            # Replace terminals in this body
            new_body = []
            for sym in body:
                if sym in terms:
                    # Create or reuse a non-terminal for this terminal
                    if sym not in terminal_map:
                        new_nt_name = f"T_{sym}"
                        while new_nt_name in nts:
                            new_nt_name += "'"
                        terminal_map[sym] = new_nt_name
                        nts.add(new_nt_name)
                    new_body.append(terminal_map[sym])
                else:
                    new_body.append(sym)
            new_bodies.append(new_body)

        new_prods[nt] = new_bodies

    # Add the terminal productions: T_a -> a
    for term, new_nt in terminal_map.items():
        new_prods[new_nt] = [[term]]

    return new_prods, nts, terms


# ==================== STEP 5 ====================
def _step5_break_long(prods, nts):
    """
    Break productions with more than 2 symbols on the RHS
    into chains of binary productions.
    e.g., A -> BCDE becomes:
        A  -> B X1
        X1 -> C X2
        X2 -> D E
    """
    new_prods = {}
    counter = [1]  # Use list for mutability in nested function

    def get_new_nt():
        name = f"X{counter[0]}"
        while name in nts:
            counter[0] += 1
            name = f"X{counter[0]}"
        counter[0] += 1
        nts.add(name)
        return name

    for nt in prods:
        new_prods[nt] = []
        for body in prods[nt]:
            if len(body) <= 2:
                new_prods[nt].append(body)
            else:
                # Break into binary chain
                current_nt = nt
                remaining = body[:]

                while len(remaining) > 2:
                    first = remaining[0]
                    remaining = remaining[1:]
                    new_nt = get_new_nt()

                    if current_nt == nt:
                        new_prods[nt].append([first, new_nt])
                    else:
                        new_prods[current_nt] = [[first, new_nt]]

                    current_nt = new_nt

                # Last two symbols
                new_prods[current_nt] = [remaining]

    return new_prods, nts


# ==================== HELPERS ====================
def _snapshot(prods, start):
    """Create a snapshot string of the current grammar state."""
    lines = []
    if start in prods:
        lines.append(_format_production(start, prods[start]))
    for nt in sorted(prods.keys()):
        if nt != start:
            lines.append(_format_production(nt, prods[nt]))
    return '\n'.join(lines)


def _format_production(nt, bodies):
    """Format a single non-terminal's productions as a string."""
    body_strs = []
    for body in bodies:
        if not body:
            body_strs.append('ε')
        else:
            body_strs.append(' '.join(body))
    return f"  {nt} → {' | '.join(body_strs)}"
