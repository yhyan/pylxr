#!/usr/bin/env python
#coding:utf-8


import os
from utils import smart_read
from langtype import LangType
import esprima

def find_tags(abspath):
    '''
    
    :param source_file: 
    :return: tag list 
    '''
    tags = []
    if os.path.isfile(abspath):
        try:
            txt = smart_read(abspath)
            mod = esprima.parseScript(txt, loc=True)
        except:
            import traceback
            print(abspath)
            print(traceback.format_exc())
            return []

    return tags






