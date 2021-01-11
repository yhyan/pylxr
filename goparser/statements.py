#coding:utf-8

"statements.py -- top-level statement parser for golang"

import collections

IGNORE = {'COMMENT1', 'COMMENTN', 'ENDL', 'WS', ' '}



bracelet_pairs = ('()', '[]', '{}')
global_statement_type = ('kw_func', 'kw_package', 'kw_type', 'kw_import', 'kw_var', 'kw_const')

def find_func_name(tokens, start):
    n = len(tokens)
    stack = []
    name_index, next_index = None, None
    while start < n:
        token = tokens[start]

        if token.type in ('(', ')', '[', ']', '{', '}'):
            for left, right in bracelet_pairs:
                if token.type == left:
                    stack.append(left)
                elif token.type == right:
                    if stack and stack[-1] == left:
                        stack.pop()
        # 找到一个func name, stack 必须是空
        elif token.type == 'NAME' and name_index is None and not stack:
            name_index = start
        elif token.type in global_statement_type and not stack and name_index is not None:
            next_index = start
            break

        start += 1
    if next_index is None:
        next_index = start
    return name_index, next_index

def find_type_name(tokens, start):
    n = len(tokens)
    stack = []
    name_index, next_index = None, None
    while start < n:
        token = tokens[start]

        if token.type in ('(', ')', '[', ']', '{', '}'):
            for left, right in bracelet_pairs:
                if token.type == left:
                    stack.append(left)
                elif token.type == right:
                    if stack and stack[-1] == left:
                        stack.pop()
        # 找到一个func name, stack 必须是空
        elif token.type == 'NAME' and name_index is None and not stack:
            name_index = start
        elif token.type in global_statement_type and not stack and name_index is not None:
            next_index = start
            break
        # print(token.type, token.value, token.lineno)
        start += 1
    if next_index is None:
        next_index = start
    return name_index, next_index


class StatementFinder:
    "see docs for parse() method"
    def __init__(self):

        self.clear()

    def clear(self):
        "clear since-statement-open state after closing a statement"
        self.open_statement = None
        self.scopes_since_open = []
        self.slices_since_open = []

    def yield_stmts(self, tokens, debug=True):
        "yield tuples from STATEMENTS for each toplevel item found in tokens"
        i = 0
        max_length = len(tokens)
        tags = []

        while i < max_length:
            tok = tokens[i]
            if tok.type == 'kw_func':
                name_index, next_index = find_func_name(tokens, i+1)
                i = next_index
                if debug:
                    print('func', tokens[name_index].value, tokens[name_index].lineno)
                tags.append((tokens[name_index].value,
                             tokens[name_index].lineno,
                             'f','',
                             ))
                continue
            elif tok.type == 'kw_type':
                name_index, next_index = find_type_name(tokens, i+1)
                i = next_index
                if debug:
                    print('type', tokens[name_index].value, tokens[name_index].lineno)
                tags.append((tokens[name_index].value,
                             tokens[name_index].lineno,
                             'm',''
                             ))
                continue
            elif tok.type == 'kw_var':
                pass
            elif tok.type == 'kw_const':
                pass
            elif tok.type == 'kw_package':
                pass
            elif tok.type == 'kw_import':
                pass
            i += 1
        return tags

    def parse(self, tokens, debug=False):
        "return list of tuples from STATEMENTS / NegativeSlice"
        return self.yield_stmts(tokens, debug)
