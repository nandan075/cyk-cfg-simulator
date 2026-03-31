"""
main.py - Entry Point for CFG Membership Checker
===================================================
Theory of Computation — Mini Project

Usage:
    python main.py           → Launches the Flask web server
    python main.py --test    → Runs built-in test cases

Then visit http://127.0.0.1:5000 in your browser.
"""

import sys


def run_tests():
    """Run built-in test cases to verify correctness."""
    from cfg_parser import parse_grammar
    from cnf_converter import convert_to_cnf
    from cyk_algorithm import cyk_algorithm

    print()
    print("=" * 60)
    print("  CFG Membership Checker — Test Suite")
    print("=" * 60)
    print()

    test_cases = [
        ("S -> aSb | ab", "ab",     True,  "a^n b^n: n=1"),
        ("S -> aSb | ab", "aabb",   True,  "a^n b^n: n=2"),
        ("S -> aSb | ab", "aaabbb", True,  "a^n b^n: n=3"),
        ("S -> aSb | ab", "aab",    False, "a^n b^n: unbalanced"),
        ("S -> aSb | ab", "abab",   False, "a^n b^n: not in language"),
        ("S -> aSb | ab", "a",      False, "a^n b^n: single char"),
        ("S -> SA | A\nA -> a", "aaa", True,  "a+ language: aaa"),
        ("S -> SA | A\nA -> a", "a",   True,  "a+ language: a"),
        ("S -> aSb | SS | ab", "aababb", True,  "Nested brackets: aababb"),
        ("S -> aSb | SS | ab", "ababab", True,  "Nested brackets: ababab"),
        ("S -> aSb | SS | ab", "aabba",  False, "Nested brackets: invalid"),
    ]

    passed = 0
    for i, (grammar, string, expected, desc) in enumerate(test_cases, 1):
        try:
            prods, start, nts, terms = parse_grammar(grammar)
            cnf_prods, cnf_start, cnf_nts, _, _ = convert_to_cnf(prods, start, nts, terms)
            accepted, _, _ = cyk_algorithm(cnf_prods, cnf_start, string, cnf_nts)

            ok = accepted == expected
            passed += ok
            status = "PASS" if ok else "FAIL"
            print(f"  Test {i:2d}: {status}  |  \"{string}\"  "
                  f"Expected: {'ACCEPT' if expected else 'REJECT'}  "
                  f"Got: {'ACCEPT' if accepted else 'REJECT'}  |  {desc}")
        except Exception as e:
            print(f"  Test {i:2d}: ERROR  |  {desc}  |  {e}")

    total = len(test_cases)
    print(f"\n  Results: {passed}/{total} passed")
    print(f"  {'All tests passed!' if passed == total else 'Some tests failed.'}\n")


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        from app import app
        print("\n  Starting CFG Membership Checker...")
        print("  Open http://127.0.0.1:5000 in your browser\n")
        app.run(debug=True, port=5000)
