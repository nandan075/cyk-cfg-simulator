"""
cfg_parser.py - Context-Free Grammar Parser
=============================================
This module handles parsing of CFG productions from text input.
It converts human-readable grammar rules into a structured dictionary
that other modules can work with.

Grammar Format:
    S -> aSb | ab | ε
    A -> aA | a

Each line represents productions for a single non-terminal.
Multiple productions are separated by '|'.
'ε' or 'epsilon' or '' represents the empty string.
"""


def parse_grammar(grammar_text):
    """
    Parse a CFG from text input into a structured dictionary.

    Args:
        grammar_text (str): Multi-line string where each line is of the form:
                            NonTerminal -> production1 | production2 | ...

    Returns:
        tuple: (productions, start_symbol, non_terminals, terminals)
            - productions: dict mapping non-terminal -> list of production bodies
              Each production body is a list of symbols (strings).
              Example: {'S': [['a', 'S', 'b'], ['a', 'b']]}
            - start_symbol: str, the first non-terminal encountered
            - non_terminals: set of all non-terminal symbols
            - terminals: set of all terminal symbols

    Raises:
        ValueError: If the grammar text is malformed or empty.
    """
    productions = {}       # {NonTerminal: [[symbol1, symbol2, ...], ...]}
    start_symbol = None     # The first non-terminal is the start symbol
    non_terminals = set()   # Uppercase letters / multi-char symbols before '->'
    terminals = set()       # Lowercase letters / symbols not in non_terminals

    lines = grammar_text.strip().split('\n')

    if not lines or all(line.strip() == '' for line in lines):
        raise ValueError("Grammar is empty. Please enter at least one production rule.")

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # ---- Validate and split the line at '->' ----
        if '->' not in line:
            raise ValueError(
                f"Line {line_num}: Missing '->' in production rule.\n"
                f"  Got: '{line}'\n"
                f"  Expected format: S -> aSb | ab"
            )

        parts = line.split('->', 1)  # Split only on the first '->'
        lhs = parts[0].strip()       # Left-hand side (non-terminal)
        rhs = parts[1].strip()       # Right-hand side (productions)

        # ---- Validate the left-hand side ----
        if not lhs:
            raise ValueError(
                f"Line {line_num}: Left-hand side of production is empty.\n"
                f"  Got: '{line}'"
            )

        # The first non-terminal encountered is the start symbol
        if start_symbol is None:
            start_symbol = lhs

        non_terminals.add(lhs)

        # ---- Parse the right-hand side ----
        # Split by '|' to get individual productions
        alternatives = rhs.split('|')

        for alt in alternatives:
            alt = alt.strip()

            # Handle empty/epsilon productions
            if alt in ('ε', 'epsilon', 'ϵ', ''):
                # Represent epsilon as an empty list
                if lhs not in productions:
                    productions[lhs] = []
                productions[lhs].append([])  # Empty list = epsilon production
                continue

            # ---- Tokenize the production body ----
            # We need to distinguish terminals from non-terminals.
            # Convention: Uppercase letters are non-terminals, lowercase are terminals.
            # Multi-character non-terminals are supported if they start with uppercase.
            body = _tokenize_production(alt, non_terminals, lhs)

            if lhs not in productions:
                productions[lhs] = []
            productions[lhs].append(body)

    # ---- Second pass: identify all non-terminals from LHS ----
    # Then determine terminals (anything in production bodies that is not a non-terminal)
    for nt in productions:
        for body in productions[nt]:
            for symbol in body:
                if symbol not in non_terminals:
                    terminals.add(symbol)

    # ---- Validate that all non-terminals used in RHS are defined ----
    for nt in productions:
        for body in productions[nt]:
            for symbol in body:
                if symbol.isupper() and len(symbol) == 1 and symbol not in non_terminals:
                    # It looks like a non-terminal but isn't defined
                    # We'll add it to non-terminals and remove from terminals
                    non_terminals.add(symbol)
                    terminals.discard(symbol)

    if start_symbol is None:
        raise ValueError("No valid production rules found in the grammar.")

    return productions, start_symbol, non_terminals, terminals


def _tokenize_production(production_str, known_non_terminals, current_lhs):
    """
    Tokenize a production body string into a list of symbols.

    Strategy:
        - Single uppercase letters are treated as non-terminals.
        - Single lowercase letters and digits are treated as terminals.
        - Known non-terminals (from LHS definitions) are recognized.

    Args:
        production_str (str): The production body string, e.g., "aSb"
        known_non_terminals (set): Set of known non-terminal symbols
        current_lhs (str): The current LHS non-terminal (for context)

    Returns:
        list: A list of symbol strings, e.g., ['a', 'S', 'b']
    """
    tokens = []
    i = 0
    production_str = production_str.strip()

    while i < len(production_str):
        ch = production_str[i]

        # Skip whitespace
        if ch == ' ':
            i += 1
            continue

        # ---- Check for multi-character non-terminals ----
        # Look for the longest match among known non-terminals
        matched = False
        for nt in sorted(known_non_terminals, key=len, reverse=True):
            if production_str[i:i+len(nt)] == nt and len(nt) > 1:
                tokens.append(nt)
                i += len(nt)
                matched = True
                break

        if matched:
            continue

        # Single character: uppercase = non-terminal, else = terminal
        tokens.append(ch)
        i += 1

    return tokens


def grammar_to_string(productions, start_symbol):
    """
    Convert a productions dictionary back into a human-readable string.

    Args:
        productions (dict): The productions dictionary.
        start_symbol (str): The start symbol.

    Returns:
        str: Multi-line string representation of the grammar.
    """
    lines = []

    # Put start symbol first
    if start_symbol in productions:
        bodies = productions[start_symbol]
        body_strs = []
        for body in bodies:
            if not body:
                body_strs.append('ε')
            else:
                body_strs.append(''.join(body))
        lines.append(f"{start_symbol} -> {' | '.join(body_strs)}")

    # Then other non-terminals
    for nt in sorted(productions.keys()):
        if nt == start_symbol:
            continue
        bodies = productions[nt]
        body_strs = []
        for body in bodies:
            if not body:
                body_strs.append('ε')
            else:
                body_strs.append(''.join(body))
        lines.append(f"{nt} -> {' | '.join(body_strs)}")

    return '\n'.join(lines)


# ===================== SAMPLE GRAMMARS =====================

SAMPLE_GRAMMARS = {
    "Balanced Parentheses: {aⁿbⁿ}": (
        "S -> aSb | ab",
        "aabb"
    ),
    "Palindromes over {a, b}": (
        "S -> aSa | bSb | a | b | ε",
        "abba"
    ),
    "Simple Arithmetic": (
        "S -> SA | A\n"
        "A -> a",
        "aaa"
    ),
    "Equal a's and b's (simple)": (
        "S -> aSb | bSa | SS | ε",
        "abba"
    ),
    "Nested Brackets": (
        "S -> aSb | SS | ab",
        "aababb"
    ),
}
