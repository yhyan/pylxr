#!/usr/bin/env python
#coding:utf-8

import ast
import os

from langtype import LangType

def visit_class(class_node):
    tags = []
    for node in class_node.body:
        node_type = node.__class__.__name__
        if node_type in ('AsyncFunctionDef', 'FunctionDef'):
            if node.name[0] != '_':
                tags.append([node.name, node.lineno, LangType.lang_py + LangType.def_func])
    return tags

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
            mod = ast.parse(txt)
        except:
            import traceback
            print(abspath)
            print(traceback.format_exc())
            return []

        for node in mod.body:
            node_type = node.__class__.__name__
            if node_type in ('AsyncFunctionDef', 'FunctionDef'):
                tags.append([node.name, node.lineno, LangType.lang_py + LangType.def_func])
            elif node_type in ('ClassDef', ):
                tags.append([node.name, node.lineno, LangType.lang_py + LangType.def_class])
                tags += visit_class(node)
            elif node_type in ('AnnAssign', 'Assign', 'AugAssign'):
                pass
    return tags






