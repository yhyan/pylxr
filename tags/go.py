#!/usr/bin/env python
# coding:utf-8

import os
from goparser import golex, statements

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
            tokens = golex.lex(txt)

            tags = statements.StatementFinder().parse(tokens)
        except:
            import traceback
            print(traceback.format_exc())
            return []

    return tags


