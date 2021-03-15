 #coding:utf-8

"statements.py -- top-level statement parser for c & cpp"

import collections
from langtype import LangType

develop_debug = False

ignore_token_type = ('COMMENTN','COMMENT1',  'NEWLINE', 'BLANK',)


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
        '(': ')',
        '{': '}',
        '[': ']',

        ')': '(',
        '}': '{',
        ']': '[',
    }

    def __init__(self):

        self.tags = []
        self.stack = []
        self.clear()

    def clear(self):
        "clear since-statement-open state after closing a statement"
        self.stack = []
        self.tags = []

    def expect_token(self, tokens, start, token_type):
        if token_type == '{':
            token_type = 'LBRACE'
        elif token_type == '}':
            token_type = 'RBRACE'

        n = len(tokens)
        while start < n:
            token = tokens[start]
            if token.type in ignore_token_type:
                start += 1
                continue

            if token.type != token_type:
                return -1
            return start
        return -1

    def goback_expect_token(self, tokens, start, token_type):
        n = len(tokens)
        while start >= 0 and start < n:
            token = tokens[start]
            if token.type in ignore_token_type:
                start -= 1
                continue

            if token.type != token_type:
                return -1
            return start
        return -1

    def goto_until_bracket(self, tokens, left_index, left_char):

        right_char = self.char_dict[left_char]
        assert tokens[left_index].value == left_char
        n = len(tokens)
        stack = [left_index, ]
        i = left_index + 1
        while i < n:
            if tokens[i].value == left_char:
                stack.append(i)
            elif tokens[i].value == right_char:
                if len(stack) == 0:
                    raise Exception("brace stack is empty, but get }")
                stack.pop()
                if len(stack) == 0:
                    return i
            i += 1
        return -1

    def find_func_name(self, tokens, start):
        id_index = self.goback_expect_token(tokens, start - 1, 'ID')
        if id_index == -1:
            if develop_debug:
                print('not goback_expect_token', start, tokens[start].value, tokens[start].lineno)
            return None, None

        rparen_index = self.goto_until_bracket(tokens, start, '(')
        if rparen_index == -1:
            if develop_debug:
                print('not goto_until_bracket', start, tokens[start].value, tokens[start].lineno)
            return None, None

        lbrace_index = self.expect_token(tokens, rparen_index + 1, '{')
        if lbrace_index == -1:
            if develop_debug:
                print('not expect_token\n', start, tokens[start].value, tokens[start].lineno)
            return None, None

        rbrace_index = self.goto_until_bracket(tokens, lbrace_index, '{')
        if rbrace_index == -1:
            if develop_debug:
                print('not goto_until_bracket\n', start, tokens[start].value, tokens[start].lineno)
            return None, None

        return id_index, rbrace_index + 1

    def find_struct_typedef_name(self, tokens, start):
        # typedef struct { type1 field1; type2 field2; } name;
        lbrace_index = self.expect_token(tokens, start + 1, 'LBRACE')
        if lbrace_index == -1:
            return None, None
        rbrack_index = self.goto_until_bracket(tokens, lbrace_index, '{')
        if rbrack_index == -1:
            return None, None
        id_index = self.expect_token(tokens, rbrack_index + 1, 'ID')
        if id_index == -1:
            return None, None
        return id_index, id_index + 1

    def find_struct_type_name(self, tokens, start):
        # struct name { type1 field1; type2 field2;};
        id_index = self.expect_token(tokens, start + 1, 'ID')
        if id_index == -1:
            return self.find_struct_typedef_name(tokens, start)

        lbrace_index = self.expect_token(tokens, id_index + 1, 'LBRACE')
        if lbrace_index == -1:
            return None, None
        rbrack_index = self.goto_until_bracket(tokens, lbrace_index, '{')
        if rbrack_index == -1:
            return None, None

        return id_index, rbrack_index + 1

    def find_define_name(self, tokens, start):
        define_index = self.expect_token(tokens, start + 1, 'DEFINE')
        if define_index == -1:
            return None, None

        id_index = self.expect_token(tokens, define_index + 1, 'ID')
        if id_index == -1:
            return None, None
        return id_index, id_index + 1

    def find_global_variable_name(self, tokens, semi_index):
        n = len(tokens)
        i = semi_index - 1
        in_bracket = False
        while i >= 0 and i < n:
            token = tokens[i]
            if token.type in ignore_token_type:
                return None
            if token.value == ')':
                in_bracket = True
            elif token.value == '(':
                in_bracket = False
            if in_bracket:
                i -= 1
                continue

            if token.type != 'ID':
                i -= 1
                continue
            return i
        return None

    def yield_tags(self, tokens):
        "yield tuples from STATEMENTS for each toplevel item found in tokens"
        i = 0
        max_length = len(tokens)

        while i < max_length:
            tok = tokens[i]
            if tok.type in ( 'STRUCT', 'ENUM',):
                name_index, next_index = self.find_struct_type_name(tokens, i)
                debug_token_type(tokens, i)
                if name_index is not None:

                    i = next_index
                    if develop_debug:
                        print('type', tokens[name_index].value, tokens[name_index].lineno)
                    self.tags.append((tokens[name_index].value,
                                 tokens[name_index].lineno,
                                 LangType.lang_c + LangType.def_struct
                                 ))
                    continue

            elif tok.type == 'DIRE':  #
                name_index, next_index = self.find_define_name(tokens,i)
                if name_index is not None:
                    # i = next_index
                    if develop_debug:
                        print('#define', tokens[name_index].value, tokens[name_index].lineno)
                    self.tags.append((tokens[name_index].value,
                                 tokens[name_index].lineno,
                                 LangType.lang_c + LangType.def_define))
            elif tok.type == 'LPAREN':
                # find '(', check if function


                debug_token_type(tokens, i)
                name_index, next_index = self.find_func_name(tokens, i)

                if name_index is not None:
                    i = next_index
                    if develop_debug:
                        print('func', tokens[name_index].value, tokens[name_index].lineno)
                    self.tags.append((tokens[name_index].value,
                                      tokens[name_index].lineno,
                                      LangType.lang_c + LangType.def_func
                                      ))
                    continue
                else:
                    self.stack.append(tokens[i].value)
            elif tok.type == 'SEMI' and len(self.stack) == 0:
                # 全局的 ; 结束的语句
                if develop_debug:
                    print(';', tokens[i].value, tokens[i].lineno)
                name_index = self.find_global_variable_name(tokens, i)
                if name_index is not None:
                    self.tags.append((tokens[name_index].value,
                                      tokens[name_index].lineno,
                                      LangType.lang_c + LangType.def_variable))

            elif tok.value in ('{', '}', '(', ')', '[', ']'):
                if tok.value in ('{', '(', '['):
                    self.stack.append(tok.value)
                else:
                    if len(self.stack) <= 0 or self.stack[-1] != self.char_dict[tok.value]:
                        print(tok.value)
                        raise Exception('%s %s' %( tokens[i].value, tokens[i].lineno))

                    self.stack.pop()


            i += 1
        return self.tags

    def parse(self, tokens, debug=False):
        "return list of tuples from STATEMENTS / NegativeSlice"
        return self.yield_tags(tokens)

