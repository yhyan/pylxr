#!/usr/bin/env python
#coding:utf-8

import os
from pycparser import parse_file
from pycparser.c_generator import CGenerator
from utils import smart_read
from tags.c import find_tags2

FNAME = os.path.join(os.path.dirname(__file__), 't0.c')


def test_statements():

    ast = parse_file(FNAME)
    #v = CGenerator()
    #v.visit(ast)
    print('finish done')
    #print(ast)
    for n in ast.ext:
        print(n)
    #    print(getattr(n, 'type', n))


def test_find_tags():
    tags = find_tags2(FNAME)
    for tag in tags:
        print(tag)

if __name__ == "__main__":
    #test_statements()
    test_find_tags()

