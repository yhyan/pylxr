#!/usr/bin/env python
# coding:utf-8

'''
https://github.com/eliben/pycparser

use pycparser parse source file 
'''

import os
import chardet
from cparser import c_lexer, statements

def find_tags(abspath):
    '''

    :param source_file: 
    :return: tag list 
    '''
    tags = []
    if os.path.isfile(abspath):
        try:
            with open(abspath, 'rb') as fp:
                txt = fp.read()
            result = chardet.detect(txt)
            encoding = result['encoding']

            # GB2312，GBK，GB18030，是兼容的，包含的字符个数：GB2312 < GBK < GB18030
            if encoding.lower() == 'gb2312':
                encoding = 'gb18030'

            txt = txt.decode(encoding)
            tokens = c_lexer.lex(txt)
            tags = statements.StatementFinder().parse(tokens)
        except:
            import traceback
            print(abspath, '\n', traceback.format_exc())
            return []

    return tags



