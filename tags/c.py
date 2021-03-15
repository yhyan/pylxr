#!/usr/bin/env python
# coding:utf-8

'''
https://github.com/eliben/pycparser

use pycparser parse source file 
'''

import os
import chardet
from cparser import c_lexer, statements

from utils import smart_read

def find_tags(abspath):
    '''

    :param source_file: 
    :return: tag list 
    '''
    tags = []
    if os.path.isfile(abspath):
        try:
            txt = smart_read(abspath)
            tokens = c_lexer.lex(txt)
            tags = statements.StatementFinder().parse(tokens)
        except:
            import traceback
            print(abspath, '\n', traceback.format_exc())
            return []

    return tags



