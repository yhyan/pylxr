import pytest, os, shutil
from . import golex, statements

FNAME = os.path.join(os.path.dirname(__file__), 'encode.go')

def test_golex():
    orig = open(FNAME).read()
    tokens = golex.lex(orig)
    assert golex.unlex(tokens) == orig


def test_statements():
    tokens = golex.lex(open(FNAME).read())
    stmts = statements.StatementFinder().parse(tokens)
    print(stmts)
    # assert sum((tokens[tup.slice] for tup in stmts), []) == tokens



if __name__ == "__main__":
    test_statements()
    test_golex()
