 #coding:utf-8

"statements.py -- top-level statement parser for c & cpp"

import sys
import collections
from langtype import LangType
from enum import Enum


import logging

logger = logging.getLogger('fordeploy')


develop_debug = False

# 'COMMENTN','COMMENT1',  'BLANK' 已经都忽略了，不会返回到token列表里。
# NEWLINE 需要用来切分全局语句，不能忽略。转义符因为没有预处理分析，所以
# 也要保留。
from .c_lexer import LPAREN, LBRACE, LBRACKET, RPAREN, RBRACE, RBRACKET,\
    NEWLINE, SEMI,\
    HASHKEY, DEFINE, INCLUDE, UNDEF, IF, IFDEF, IFNDEF, ELIF, ELSE, ENDIF, \
    TYPEDEF, STRUCT, UNION, ENUM, \
    ID, COMMA, EQUALS


small_bracket_compound_statement = 200
mid_bracket_compound_statement = 201
large_bracket_compound_statement = 202

include_node = 203
define_node = 204
undef_node = 205
line_macro_node = 206
error_macro_node = 207
pragma_macro_node = 208

if_macro_node = 209
ifdef_macro_node = 210
ifndef_macro_node = 211
elif_macro_node = 212
else_macro_node = 213
endif_macro_node = 214

def is_terminal_node(token):
    return token.type < 200


class NonTerminalNode(object):
    def __init__(self, tokens, node_type, **kwargs):
        # tokens[start_index:end_index+1]
        self.tokens = tokens
        self.n = len(tokens)
        self.type = node_type
        self.kwargs = kwargs

    def get_first_id(self):
        i = 0
        while i < self.n:
            if self.tokens[i].type == ID:
                return self.tokens[i]
            i += 1
        return None

    def get_str(self, end=''):
        #logger.debug('start nontermial node:')
        return ''.join([t.value for t in self.tokens])

    def __str__(self):
        return 'NonTermial(start_line=%s, start_value=%s, end_line=%s, env_value=%s, type=%s)' % (
            self.tokens[0].lineno,
            self.tokens[0].value,
            self.tokens[-1].lineno,
            self.tokens[-1].value,
            self.type)

    def __repr__(self):
        return self.__str__()


    def get_token_list(self):
        tokens = self.tokens
        if self.type in (if_macro_node, ifdef_macro_node, ifndef_macro_node):
            terminal_token_list = []
            i = 3
            n = self.n

            # if 0
           # print(tokens[2], tokens[1], tokens[0], tokens[3])
            if self.type == if_macro_node and tokens[2].value in (0, '0'):
                return []

            end_index = -1
            while i < n:
                if tokens[i-1].type == HASHKEY and tokens[i].type in (ELIF, ELSE, ENDIF):
                    end_index = i - 2
                    break
                else:
                    i += 1
            i = 0
            while  i < n and tokens[i].type != NEWLINE:
                i += 1

            while i <= end_index:
                node = self.tokens[i]
                if is_terminal_node(node):
                    terminal_token_list.append(node)
                else:
                    terminal_token_list += node.get_token_list()
                i += 1
            return terminal_token_list
        else:
            return tokens



def debug_token_type(tokens, i):
    if not develop_debug:
        return
    n = len(tokens)
    for t in range(i-5, i+20):
        if t >= 0 and t < n:
            print(t, tokens[t].type, tokens[t].value[0:5], tokens[t].lineno)
    print()





class StatementFinder(object):
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

        DEFINE: define_node,
        INCLUDE: include_node,
        UNDEF: undef_node,

        IF:if_macro_node,
        IFDEF:ifdef_macro_node,
        IFNDEF:ifndef_macro_node,
        ELIF:elif_macro_node,
        ELSE:else_macro_node,
        ENDIF:endif_macro_node,
    }

    def __init__(self, tokens=[], lines=[]):
        self.lines = lines
        self.tokens = tokens
        self.n = 0
        self.tags = []
        self.nodes = []
        self.defines = {}

    def input(self, tokens):
        assert  isinstance(tokens, list)
        assert len(tokens) > 0, "input tokens list can't be empty"
        self.tokens = tokens
        self.n = len(tokens)
        self.tags = []
        self.nodes = []
        self.defines = {}


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

        # 忽略函数声明
        if len(node_list) >= 2:
            if node_list[-1].type == small_bracket_compound_statement \
                    and node_list[-2].type == ID:
                logger.debug("ignore func declartion %s " % node_list[-2].value)
                return []


        # typedef, 变量定义
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
        bracket_stack = [j]
        j += 1
        n = len(tokens)
        while j < n:
            if tokens[j].type in set([LPAREN, LBRACE, LBRACKET]):
                bracket_stack.append(j)
            elif tokens[j].type == self.char_dict[tokens[bracket_stack[-1]].type]:
                bracket_stack.pop()
                if len(bracket_stack) == 0:
                    return j
            j += 1
        if j >= n and len(bracket_stack) == 0:
            return j
        raise Exception("can't find right bracket: %s" % tokens[bracket_stack[-1]])



    def find_decl(self, i, tokens):
        n = len(tokens)

        node_list = []

        while i < n:
            tok = tokens[i]
            logger.debug('%s %s' % (tokens[i], i))

            if tok.type in set([LPAREN, LBRACE, LBRACKET]):

                next_i = self.find_right_bracket(i, tokens)

                node_list.append(NonTerminalNode(tokens[i:next_i+1], self.non_term_type_dict[tok.type]))
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
        while i < max_length:
            # find new global statement
            decl, next_i = self.find_decl(i, tokens)
            i = next_i
            if decl is not None:
                global_decls.append(decl)

        return global_decls


    def find_if_macro_node(self, i):
        # tokens[i,i+1] == #if or #ifdef #ifndef

        n = self.n
        tokens = self.tokens
        token_type = tokens[i+1].type
        my_nodes = [tokens[i], tokens[i+1]]

        j = i + 2
        while j < n:
            # endif 结束
            if tokens[j-1].type == HASHKEY and tokens[j].type == ENDIF:
                my_nodes.append(tokens[j])
                node = NonTerminalNode(my_nodes, self.non_term_type_dict[token_type])
                return node, j+1
            elif tokens[j-1].type == HASHKEY and tokens[j].type in (IF, IFDEF, IFNDEF):
                # 上次多 append 了一个 #，删除
                my_nodes.pop()
                node, next_j = self.find_if_macro_node(j-1)
                if node is not None:
                    my_nodes.append(node)
                j = next_j
            else:
                my_nodes.append(tokens[j])
                j += 1
        raise Exception("can't find #endif: %s" % my_nodes[-1] if len(my_nodes) > 0 else tokens[-1])


    def find_macro_node(self, i):
        # self.tokens[i] == '#'
        n = self.n
        tokens = self.tokens
        # end of tokens
        if i+1 >= n:
            return None, n
        token_type = tokens[i+1].type
        if token_type == DEFINE:
            j = i + 2
            while j < n and tokens[j].type != NEWLINE:
                j += 1
            if j == n:
                return None, n
            node = NonTerminalNode(tokens[i:j], define_node)
            return node, j
        elif token_type == INCLUDE:
            # 忽略 #include 指令
            j = i + 2
            while j < n and tokens[j].type != NEWLINE:
                j += 1
            return None, j
        elif token_type == UNDEF:
            # 忽略undef指令
            j = i + 2
            if j < n and tokens[j].type == ID:
                self.defines.pop(tokens[j].value,'')
            while j < n and tokens[j].type != NEWLINE:
                j += 1
            return None, j
        elif token_type in (IF, IFDEF, IFNDEF):
            node, next_i = self.find_if_macro_node(i)
            return node, next_i
        else:
            while i < n and tokens[i].type != NEWLINE:
                i += 1
            return None, i



    def parse_macros(self):
        i = 0
        n = self.n
        while i < n:
            if self.tokens[i].type == HASHKEY:
                macro_node, next_i = self.find_macro_node(i)
                if macro_node:
                    self.nodes.append(macro_node)
                i = next_i
            else:
                self.nodes.append(self.tokens[i])
                i += 1
       # print('finish parse macro nodes')

        terminal_token_list = []
        for node in self.nodes:
            if is_terminal_node(node):
                terminal_token_list.append(node)
                #print(node)
            else:
              #for lino in range(node.tokens[0].lineno, node.tokens[-1].lineno+1):
              #    print("%04d %s" % (lino, self.lines[lino-1]))
              #print('\n')
              #print(' '.join([t.value for t in node.get_token_list()]))
              #print('\n')
              #print(node)
              #print('\n'*3)
              #
              #for t in node.tokens:
              #    print(t)

                terminal_token_list += node.get_token_list()
        return terminal_token_list




    def print_decl(self, decl):
        strs = []
        strs.append('start statement:')
        for node in decl:
            if isinstance(node, NonTerminalNode):
                strs.append(node.get_str())
            else:
                strs.append("%s" % node.value)
        s = ''.join(strs) + '\n'
        logger.debug(s)



    def parse(self, tokens):
        "return list of tuples from STATEMENTS / NegativeSlice"

        self.input(tokens)

        tokens = self.parse_macros()
       # s = (' '.join([t.value for t in tokens]))
       # with open('/tmp/t.c', 'w') as fp:
       #     fp.write(s)

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



