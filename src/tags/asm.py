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
                semi_index = li.find(';')
                if semi_index >= 0:
                    li = li[:semi_index]
                    li = li.strip()
                if not li:
                    continue

                if li.endswith(':'):
                    match_obj = re.search(identifier, li[:-1])
                    if match_obj is not None and match_obj.group() == li[:-1]:
                        tags.append([
                            li[:-1], line_number, LangType.lang_c + LangType.def_func
                        ])
                eq_index = li.find('=')
                if eq_index >= 0:
                    word = li[:eq_index].strip()
                    match_obj = re.search(identifier, word)
                    if match_obj is not None and match_obj.group() == word:
                        tags.append([
                            word, line_number, LangType.lang_c + LangType.def_variable
                        ])



        except:
            import traceback
            print(abspath)
            print(traceback.format_exc())
            return []


    return tags
