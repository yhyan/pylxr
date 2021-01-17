#!/usr/bin/env python
# coding:utf-8

'''
https://github.com/eliben/pycparser

use pycparser parse source file 
'''

import os
from cparser import c_lexer, statements

def find_tags(abspath):
    '''

    :param source_file: 
    :return: tag list 
    '''
    tags = []
    if os.path.isfile(abspath):
        try:
            with open(abspath) as fp:
                txt = fp.read()
            tokens = c_lexer.lex(txt)

            tags = statements.StatementFinder().parse(tokens)
        except:
            import traceback
            print(traceback.format_exc())
            return []

    return tags



