import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from gnf import convert_to_gnf

def assert_valid(grammar):
    r = convert_to_gnf(grammar)
    assert r["ok"]
    assert r["complete_gnf"], (grammar, r["result"], r["stages"][-1])

def test_simple():
    assert_valid("""S -> AB | a
A -> a
B -> b""")

def test_unit():
    assert_valid("""S -> A
A -> a""")

def test_epsilon():
    assert_valid("""S -> AB | a
A -> ε | a
B -> b""")

def test_left_recursion():
    assert_valid("""S -> S a | b""")

def test_indirect_left_recursion():
    assert_valid("""S -> A a | b
A -> S c | d""")

def test_multiple_variables():
    assert_valid("""S -> A B | C
A -> a
B -> b
C -> c""")

if __name__ == "__main__":
    test_simple()
    test_unit()
    test_epsilon()
    test_left_recursion()
    test_indirect_left_recursion()
    test_multiple_variables()
    print("All GNF tests passed.")
