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

def visit_Decl(node, **kwargs):
    return visit_node(node.type, **kwargs)

def visit_ArrayDecl(node, **kwargs):
    return visit_node(node.type, **kwargs)

def visit_PtrDecl(node, **kwargs):
    return visit_node(node.type, **kwargs)

def visit_FuncDecl(node, **kwargs):
    return visit_node(node.type, **kwargs)

def visit_TypeDecl(node, **kwargs):
    print(node)
    if node.type == 'define':
        return [(node.declname, node.coord.line, LangType.c_variable)]
    if node.type.__class__.__name__ == 'IdentifierType':
        return [(node.declname, node.coord.line, LangType.c_variable)]
    else:
        tags = [(node.declname, node.coord.line, LangType.c_struct)]
        tags += visit_node(node.type)
        return tags

def visit_Struct(node, **kwargs):
    # struct decls 是Node，则只是定义
    if node.decls is not None:
        tag_type = LangType.c_struct
        return [(node.name, node.coord.line, tag_type)]
    return []

def visit_Enum(node, **kwargs):
    return [(node.name, node.coord.line, LangType.c_struct)]

def visit_Union(node, **kwargs):
    return [(node.name, node.coord.line, LangType.c_struct)]

def visit_FuncDef(node):
    decl = node.decl
    return [(decl.name, decl.coord.line, LangType.c_func)]

def visit_Typedef(node, **kwargs):
    return visit_node(node.type, **kwargs)

def visit_node(node, **kwargs):
    node_type = node.__class__.__name__
    func = globals().get("visit_%s" % node_type, None)
    if func is not None:
         return func(node, **kwargs)
    return []


def find_tags2(abspath, yacc_debug=False):
    tags = []
    if os.path.isfile(abspath):
        try:
            mod = parse_file(abspath, yacc_debug=yacc_debug)
            if mod is None:
                return tags
            for node in mod.ext:
                tags += visit_node(node)
        except:
            import traceback
            print(abspath, '\n', traceback.format_exc())
            return []

    return tags



