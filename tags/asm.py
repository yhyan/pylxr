#!/usr/bin/env python
#coding:utf-8

import re
import os

from utils import smart_read
from langtype import LangType

def find_tags(abspath):
    '''
    :param source_file: 
    :return: tag list 
    '''
    tags = []
    identifier = r'[a-zA-Z_$][0-9a-zA-Z_$]*'

    if os.path.isfile(abspath):
        try:
            txt = smart_read(abspath)
            lines = txt.split('\n')
            line_number = 0
            for li in lines:
                li = li.strip()
                line_number += 1
                if not li:
                    continue
                if li[0]  == ';':
                    continue
                if li.endswith(':'):
                    match_obj = re.search(identifier, li[:-1])
                    if match_obj is not None and match_obj.group() == li[:-1]:
                        tags.append([
                            li[:-1], line_number, LangType.lang_c + LangType.def_func
                        ])

        except:
            import traceback
            print(abspath)
            print(traceback.format_exc())
            return []


    return tags
