#!/usr/bin/env python
#coding:utf-8

import ast
import os
from utils import smart_read
import javalang

from langtype import LangType

def find_tags(abspath):
    '''
    
    :param source_file: 
    :return: tag list 
    '''
    tags = []
    if os.path.isfile(abspath):


        try:
            txt = smart_read(abspath)
            mod = javalang.parse.parse(txt)
        except:
            import traceback
            print(abspath)
            print(traceback.format_exc())
            return []

    return tags






