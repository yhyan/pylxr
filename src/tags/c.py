#!/usr/bin/env python
# coding:utf-8

'''
https://github.com/eliben/pycparser

use pycparser parse source file 
'''

import os
from cparser import c_lexer, statements
from pycparser import parse_file

from langtype import LangType
from utils import smart_read

def find_tags(abspath):
    '''
    :param source_file: 
    :return: tag list 
    '''
    # return find_tags2(abspath)

    tags = []
    if os.path.isfile(abspath):
        try:
            txt = smart_read(abspath)
            tokens = c_lexer.lex(txt)
            lines = txt.split('\n')
            parser = statements.StatementFinder(tokens, lines)
            tags = parser.parse(tokens)
        except:
            import traceback
            print(abspath, '\n', traceback.format_exc())
            return []

    return tags




