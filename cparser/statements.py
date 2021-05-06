 #coding:utf-8

"statements.py -- top-level statement parser for c & cpp"

import sys
import collections
from langtype import LangType
from enum import Enum


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



develop_debug = False

# 'COMMENTN','COMMENT1',  'BLANK' 已经都忽略了，不会返回到token列表里。
# NEWLINE 需要用来切分全局语句，不能忽略。转义符因为没有预处理分析，所以
# 也要保留。
from .c_lexer import LPAREN, LBRACE, LBRACKET, RPAREN, RBRACE, RBRACKET,\
    NEWLINE, SEMI,\
    HASHKEY, DEFINE,\
    TYPEDEF, STRUCT, UNION, ENUM, \
    ID, COMMA, EQUALS


small_bracket_compound_statement = 0
mid_bracket_compound_statement = 1
large_bracket_compound_statement = 2

class NonTerminalNode(object):
    def __init__(self, tokens, start_index, end_index, node_type):
        # tokens[start_index:end_index+1]
        self.tokens = tokens
        self.start_index = start_index
        self.end_index = end_index
        self.type = node_type

    def get_first_id(self):
        i = self.start_index
        while i <= self.end_index:
            if self.tokens[i].type == ID:
                return self.tokens[i]
            i += 1
        return None

    def print_value(self, end=''):
        #logger.debug('start nontermial node:')
        return ''.join([self.tokens[i].value for i in range(self.start_index, self.end_index+1)])

    def __str__(self):
        return 'NonTermial(i=%s,j=%s, type=%s)' % (self.start_index, self.end_index, self.type)

    def __repr__(self):
        return self.__str__()




def debug_token_type(tokens, i):
    if not develop_debug:
        return
    n = len(tokens)
    for t in range(i-5, i+20):
        if t >= 0 and t < n:
            print(t, tokens[t].type, tokens[t].value[0:5], tokens[t].lineno)
    print()





class StatementFinder:
    "see docs for parse() method"

    char_dict = {
        LPAREN: RPAREN,
        LBRACE: RBRACE,
        LBRACKET: RBRACKET,

        RPAREN: LPAREN,
        RBRACE: LBRACE,
        RBRACKET: LBRACKET,
    }

    non_term_type_dict = {
        LPAREN: small_bracket_compound_statement,
        LBRACKET: mid_bracket_compound_statement,
        LBRACE: large_bracket_compound_statement,
    }

    def __init__(self, tokens=[]):
        self.tokens = tokens
        self.tags = []


    def parse_tag_from_decl(self, node_list):
        '''
        
        一个 node 是一个token或者一个 NonTerminalNode

        解析全局的 declaration 或者 func definition
        
        返回 identifier list
        '''
        n = len(node_list)

        if n <= 2:
            return []


        # define 语句
        if node_list[0].type == HASHKEY:
            if node_list[1].type == DEFINE:
                node = node_list[2]
                if node.type == ID:
                    return [(node.value, node.lineno,LangType.c_define)]
            else:
                # 其它预处理全部忽略
                return []

        # 函数定义
        i = n-1
        while node_list[i].type == NEWLINE:
            i -= 1
        if i >= 1 and node_list[i].type == large_bracket_compound_statement and \
                        node_list[i-1].type == small_bracket_compound_statement:
            i = i-2
            while i >= 0:
                node = node_list[i]
                if node.type == ID:
                    return [(node.value, node.lineno,LangType.c_func)]
                i -= 1
            return []


        # typedef
        tag_list = []
        i = n-1
        finding = True
        is_typedef = node_list[0].type == TYPEDEF
        tag_type = LangType.c_define if is_typedef else LangType.c_variable

        while i >= 0:
            node = node_list[i]
            if i > 0 and node_list[i-1].type == EQUALS:
                i -= 2
                continue

            if node.type == large_bracket_compound_statement:
                if i - 2 >= 0 and node_list[i-2].type in (STRUCT, UNION, ENUM):
                    node = node_list[i-1]
                    if node.type == ID:
                        tag_list.append((node.value, node.lineno, LangType.c_struct))
                        break



            if finding:
                if node.type == ID:
                    tag_list.append((node.value, node.lineno, tag_type))
                    finding = False
                elif node.type == small_bracket_compound_statement:
                    token = node.get_first_id()
                    if token is not None:
                        tag_list.append((token.value, token.lineno, tag_type))
                        finding = False
            else:
                if node.type == COMMA:
                    finding = True

            i -= 1

        return tag_list


    def find_right_bracket(self, j, tokens):
        bracket_stack = [tokens[j].type]
        j += 1
        n = len(tokens)
        while j < n:
            if tokens[j].type in set([LPAREN, LBRACE, LBRACKET]):
                bracket_stack.append(tokens[j].type)
            elif tokens[j].type == self.char_dict[bracket_stack[-1]]:
                bracket_stack.pop()
                if len(bracket_stack) == 0:
                    return j
            j += 1
        raise Exception("can't find right bracket")



    def find_decl(self, i, tokens):
        n = len(tokens)

        node_list = []

        while i < n:
            tok = tokens[i]
            # logger.info('%s %s %s %s' % (tokens[j], tokens[i], j, i))

            if tok.type in set([LPAREN, LBRACE, LBRACKET]):

                next_i = self.find_right_bracket(i, tokens)

                node_list.append(NonTerminalNode(tokens, i, next_i, self.non_term_type_dict[tok.type]))
               # print(node_list)
                # (){} 语句后面一个换行符 表示函数

                if len(node_list) >= 2 and node_list[-2].type == small_bracket_compound_statement and (
                                    next_i + 1 >= n or tokens[next_i + 1].type == NEWLINE
                ):
                    return node_list, next_i+2


                i = next_i + 1

                # 有可能最后一个token不是 NEWLINE 和 SEMI
                if i >= n:
                    return node_list, i

            elif tok.type == NEWLINE:

                if len(node_list) > 0 and node_list[0].type == HASHKEY:
                    node_list.append(tok)
                    return node_list, i + 1
                else:
                    i = i + 1

            # get new global node
            elif tok.type == SEMI:
                return node_list, i+1

            else:
                # other node
                node_list.append(tokens[i])
                i = i + 1
        return None, n+1

    def parse_global_decls(self, tokens):

        "yield tuples from STATEMENTS for each toplevel item found in tokens"

        global_decls = []
        max_length = len(tokens)

        i = 0
        last_j = None
        while i < max_length:
            # find new global statement

            decl, next_i = self.find_decl(i, tokens)
            i = next_i
            if decl is not None:
                global_decls.append(decl)





        return global_decls


    def print_decl(self, decl):
        print('start statement:')
        for node in decl:
            if isinstance(node, NonTerminalNode):
                print(node.print_value(), end='')
            else:
                print("%s" % node.value, end='')
        print()


    def parse(self, tokens, debug=False):
        "return list of tuples from STATEMENTS / NegativeSlice"
        decls = self.parse_global_decls(tokens)

        tag_list = []
        for decl in decls:
           # self.print_decl(decl)
            tags = self.parse_tag_from_decl(decl)
            if len(tags) > 0:
                tag_list += tags
            #    for tag in tags:
            #        print(tag)

        return tag_list



