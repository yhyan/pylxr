#!/usr/bin/env python
#coding:utf-8

import os
from pycparser import parse_file

from utils import smart_read

FNAME = os.path.join(os.path.dirname(__file__), 'test.c')


def test_statements():

    ast = parse_file(FNAME)
    print(ast)




if __name__ == "__main__":
    test_statements()
    #test_golex()
    #test_all_python_source_code()
