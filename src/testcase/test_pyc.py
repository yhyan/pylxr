#!/usr/bin/env python
#coding:utf-8

import os
import sys
from pycparser import parse_file
from pycparser.c_generator import CGenerator
from pycparser.c_parser import CParser
from utils import smart_read
from tags.c import find_tags2

FNAME = os.path.join(os.path.dirname(__file__), 't0.c')


def test_tokens(f):
    parser = CParser(yacc_debug=True)
    parser.clex.filename = f
    parser.clex.reset_lineno()
    txt = smart_read(f)
    parser.clex.input(txt)
    token = parser.clex.token()
    while token:
        print(token)
        token = parser.clex.token()

def test_statements(f):

    ast = parse_file(f, yacc_debug=True)
    #v = CGenerator()
    #v.visit(ast)
    print('finish done')
    #print(ast)
    for n in ast.ext:
        print(n)
    #    print(getattr(n, 'type', n))


def test_find_tags(f):
    tags = find_tags2(f, yacc_debug=True)
    for tag in tags:
        print(tag)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        f = sys.argv[1]
    else:
        f = FNAME

    test_tokens(f)
    test_statements(f)
    test_find_tags(f)



