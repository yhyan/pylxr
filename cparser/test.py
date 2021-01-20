import pytest, os, shutil
from . import c_lexer
from . import statements

FNAME = os.path.join(os.path.dirname(__file__), 'test.c')

def test_golex():
    orig = open(FNAME).read()
    tokens = c_lexer.lex(orig)
    ss = [t.value for t in tokens]
    print(''.join(ss))
    #for token in tokens:
    #    print('%stoken.value,)
    assert c_lexer.unlex(tokens) == orig

    type_set = set()
    for t in tokens:
        type_set.add(t.type)
    print(type_set)

def test_all_python_source_code():
    CURDIR = os.path.abspath(os.path.dirname(__file__))
    project_path = os.path.abspath(os.path.join(CURDIR, '..'))

    # source_dir = os.path.abspath(os.path.join(project_path, 'data/source/redis/3.0'))
    source_dir = os.path.abspath(os.path.join(project_path, 'data/source/python/cpython-3.8.3'))
    files = []
    for i in os.walk(source_dir):
        for f in i[2]:
            if f.endswith('.c') or f.endswith('.h'):
                files.append(os.path.join(i[0], f))
    type_set = set()
    for f in files:
        print('start test %s ..' % f)
        with open(f) as fp:
            txt = fp.read()
        tokens = c_lexer.lex(txt)
        for t in tokens:
            type_set.add(t.type)
    print(type_set)


def test_statements():
    tokens = c_lexer.lex(open(FNAME).read())
    stmts = statements.StatementFinder().parse(tokens)
    print(stmts)
    # assert sum((tokens[tup.slice] for tup in stmts), []) == tokens



if __name__ == "__main__":
    test_statements()
    #test_golex()
    #test_all_python_source_code()