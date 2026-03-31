"""
app.py - Flask Web Application for CFG Membership Checker
============================================================
Serves the HTML interface and processes grammar/string
submissions using the Python backend modules.

Run:
    python app.py
Then visit http://127.0.0.1:5000 in your browser.
"""

from flask import Flask, render_template, request
from cfg_parser import parse_grammar, SAMPLE_GRAMMARS
from cnf_converter import convert_to_cnf
from cyk_algorithm import cyk_algorithm

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main route:
        GET  -> Render the form (optionally pre-filled with a sample grammar)
        POST -> Parse grammar, convert to CNF, run CYK, render results
    """

    # ---- Default values for template ----
    grammar_text = ""
    input_string = ""
    result = None          # Will hold the final result dict
    error = None           # Error message string
    cnf_steps = None       # CNF conversion steps list
    cyk_table_data = None  # Formatted CYK table for display
    cyk_steps = None       # Step-by-step CYK execution
    selected_sample = ""   # Which sample is currently selected

    # ---- Handle sample grammar loading (GET with query param) ----
    if request.method == "GET":
        sample_key = request.args.get("sample", "")
        if sample_key and sample_key in SAMPLE_GRAMMARS:
            grammar_text, input_string = SAMPLE_GRAMMARS[sample_key]
            selected_sample = sample_key

    # ---- Handle form submission (POST) ----
    if request.method == "POST":
        grammar_text = request.form.get("grammar", "").strip()
        input_string = request.form.get("string", "").strip()
        selected_sample = request.form.get("selected_sample", "")

        if not grammar_text:
            error = "Please enter at least one grammar production rule."
        else:
            try:
                # Step 1: Parse the grammar
                productions, start_symbol, non_terminals, terminals = parse_grammar(grammar_text)

                # Step 2: Convert to CNF
                cnf_prods, cnf_start, cnf_nts, cnf_terms, cnf_steps = convert_to_cnf(
                    productions, start_symbol, non_terminals, terminals
                )

                # Step 3: Run CYK Algorithm
                accepted, table, cyk_steps_raw = cyk_algorithm(
                    cnf_prods, cnf_start, input_string, cnf_nts
                )

                # Build the CYK table for HTML rendering
                n = len(input_string)
                cyk_table_data = _build_table_data(table, input_string, accepted, cnf_start)
                cyk_steps = cyk_steps_raw

                # Build result
                display_str = input_string if input_string else "ε"
                result = {
                    "accepted": accepted,
                    "string": display_str,
                    "start_symbol": cnf_start,
                    "non_terminals": sorted(non_terminals),
                    "terminals": sorted(terminals),
                }

            except ValueError as e:
                error = str(e)
            except Exception as e:
                error = f"Unexpected error: {e}"

    return render_template(
        "index.html",
        grammar_text=grammar_text,
        input_string=input_string,
        result=result,
        error=error,
        cnf_steps=cnf_steps,
        cyk_table=cyk_table_data,
        cyk_steps=cyk_steps,
        selected_sample=selected_sample,
        sample_grammars=SAMPLE_GRAMMARS,
    )


def _build_table_data(table, input_string, accepted, start_symbol):
    """
    Convert the CYK table into a structured dict for easy HTML rendering.

    Returns:
        dict with keys:
            - 'chars': list of characters in the input string
            - 'n': length of input string
            - 'rows': list of rows, each row is a list of cell dicts
                Each cell: {'content': str, 'class': str}
            - 'accepted': bool
            - 'final_cell': str (content of top-right cell)
            - 'start_symbol': str
    """
    n = len(input_string)
    if n == 0:
        return {"chars": [], "n": 0, "rows": [], "accepted": accepted,
                "final_cell": "∅", "start_symbol": start_symbol}

    rows = []
    for length in range(1, n + 1):
        row = []
        for start_pos in range(n):
            end_pos = start_pos + length - 1
            if end_pos < n:
                cell = table[start_pos][end_pos]
                content = ", ".join(sorted(cell)) if cell else "·"

                # Determine cell CSS class
                if start_pos == 0 and end_pos == n - 1:
                    css = "cell-final-accept" if accepted else "cell-final-reject"
                elif cell:
                    css = "cell-filled"
                else:
                    css = "cell-empty"

                row.append({"content": content, "css": css})
            else:
                row.append({"content": "", "css": "cell-na"})
        rows.append({"length": length, "cells": row})

    final_cell_set = table[0][n - 1]
    final_cell = ", ".join(sorted(final_cell_set)) if final_cell_set else "∅"

    return {
        "chars": list(input_string),
        "n": n,
        "rows": rows,
        "accepted": accepted,
        "final_cell": final_cell,
        "start_symbol": start_symbol,
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
