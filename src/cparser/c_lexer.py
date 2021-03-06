#------------------------------------------------------------------------------
# pycparser: c_lexer.py
#
# CLexer class: lexer for the C language
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#------------------------------------------------------------------------------
import re
import sys

import ply
from ply.lex import TOKEN

import logging

logger = logging.getLogger('fordeploy')

# reference：https://github.com/eliben/pycparser.git

##
## Reserved keywords
##
keywords = (
    '_BOOL', '_COMPLEX', 'AUTO', 'BREAK', 'CASE', 'CHAR', 'CONST',
    'CONTINUE', 'DEFAULT', 'DO', 'DOUBLE', 'ELSE', 'ENUM', 'EXTERN',
    'FLOAT', 'FOR', 'GOTO', 'IF', 'INLINE', 'INT', 'LONG', 'VA_LIST',
    'REGISTER', 'OFFSETOF',
    'RESTRICT', 'RETURN', 'SHORT', 'SIGNED', 'SIZEOF', 'STATIC', 'STRUCT',
    'SWITCH', 'TYPEDEF', 'UNION', 'UNSIGNED', 'VOID',
    'VOLATILE', 'WHILE', '__INT128',

    # 预处理
    'DEFINE', 'UNDEF', 'INCLUDE', 'IFDEF', 'IFNDEF', 'ELIF', 'DEFINED', 'ENDIF'
)

keyword_map = {}
for keyword in keywords:
    if keyword == '_BOOL':
        keyword_map['_Bool'] = keyword
    elif keyword == '_COMPLEX':
        keyword_map['_Complex'] = keyword
    else:
        keyword_map[keyword.lower()] = keyword

##
## All the tokens recognized by the lexer
##
c_tokens = keywords + (
    # Identifiers
    'ID',

    # 'COMMENTN','COMMENT1',
    'HASHKEY',
    # Type identifiers (identifiers previously defined as
    # types with typedef)
    # 'TYPEID',

    # constants
    'INT_CONST_DEC', 'INT_CONST_OCT', 'INT_CONST_HEX', 'INT_CONST_BIN', 'INT_CONST_CHAR',
    'FLOAT_CONST', 'HEX_FLOAT_CONST',
    'CHAR_CONST',
    'WCHAR_CONST',

    # String literals
    'STRING_LITERAL',
    'WSTRING_LITERAL',

    # 'WS',
    'NEWLINE', 'BLANK',

    # Operators
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'OR', 'AND', 'NOT', 'XOR', 'LSHIFT', 'RSHIFT',
    'LOR', 'LAND', 'LNOT',
    'LT', 'LE', 'GT', 'GE', 'EQ', 'NE',

    'ESC',

    # Assignment
    'EQUALS', 'TIMESEQUAL', 'DIVEQUAL', 'MODEQUAL',
    'PLUSEQUAL', 'MINUSEQUAL',
    'LSHIFTEQUAL', 'RSHIFTEQUAL', 'ANDEQUAL', 'XOREQUAL',
    'OREQUAL',

    # Increment/decrement
    'PLUSPLUS', 'MINUSMINUS',

    # Structure dereference (->)
    'ARROW',

    # Conditional operator (?)
    'CONDOP',

    # Delimeters
    'LPAREN', 'RPAREN',  # ( )
    'LBRACKET', 'RBRACKET',  # [ ]
    'LBRACE', 'RBRACE',  # { }
    'COMMA', 'PERIOD',  # . ,
    'SEMI', 'COLON',  # ; :

    # Ellipsis (...)
    'ELLIPSIS',

    # pre-processor
    'PPHASH',  # '#'
    'PPPRAGMA',  # 'pragma'
    'PPPRAGMASTR',
)

# for _name, j in enumerate(c_tokens):
#    globals()[_name] = j + 1


_BOOL = 1
_COMPLEX = 2
AUTO = 3
BREAK = 4
CASE = 5
CHAR = 6
CONST = 7
CONTINUE = 8
DEFAULT = 9
DO = 10
DOUBLE = 11
ELSE = 12
ENUM = 13
EXTERN = 14
FLOAT = 15
FOR = 16
GOTO = 17
IF = 18
INLINE = 19
INT = 20
LONG = 21
VA_LIST = 22
REGISTER = 23
OFFSETOF = 24
RESTRICT = 25
RETURN = 26
SHORT = 27
SIGNED = 28
SIZEOF = 29
STATIC = 30
STRUCT = 31
SWITCH = 32
TYPEDEF = 33
UNION = 34
UNSIGNED = 35
VOID = 36
VOLATILE = 37
WHILE = 38
__INT128 = 39
DEFINE = 40
UNDEF = 41
INCLUDE = 42
IFDEF = 43
IFNDEF = 44
ELIF = 45
DEFINED = 46
ENDIF = 47
ID = 48
HASHKEY = 49
INT_CONST_DEC = 50
INT_CONST_OCT = 51
INT_CONST_HEX = 52
INT_CONST_BIN = 53
INT_CONST_CHAR = 54
FLOAT_CONST = 55
HEX_FLOAT_CONST = 56
CHAR_CONST = 57
WCHAR_CONST = 58
STRING_LITERAL = 59
WSTRING_LITERAL = 60
NEWLINE = 61
BLANK = 62
PLUS = 63
MINUS = 64
TIMES = 65
DIVIDE = 66
MOD = 67
OR = 68
AND = 69
NOT = 70
XOR = 71
LSHIFT = 72
RSHIFT = 73
LOR = 74
LAND = 75
LNOT = 76
LT = 77
LE = 78
GT = 79
GE = 80
EQ = 81
NE = 82
ESC = 83
EQUALS = 84
TIMESEQUAL = 85
DIVEQUAL = 86
MODEQUAL = 87
PLUSEQUAL = 88
MINUSEQUAL = 89
LSHIFTEQUAL = 90
RSHIFTEQUAL = 91
ANDEQUAL = 92
XOREQUAL = 93
OREQUAL = 94
PLUSPLUS = 95
MINUSMINUS = 96
ARROW = 97
CONDOP = 98
LPAREN = 99
RPAREN = 100
LBRACKET = 101
RBRACKET = 102
LBRACE = 103
RBRACE = 104
COMMA = 105
PERIOD = 106
SEMI = 107
COLON = 108
ELLIPSIS = 109
PPHASH = 110
PPPRAGMA = 111
PPPRAGMASTR = 112



class CTok(object):


    def find_tok_column(self, token):
        """ Find the column of the token in its line.
        """
        last_cr = token.lexer.lexdata.rfind('\n', 0, token.lexpos)
        return token.lexpos - last_cr

    tokens = c_tokens

    ######################--   PRIVATE   --######################

    ##
    ## Internal auxiliary methods
    ##
    def _error(self, msg, token):
        location = self._make_tok_location(token)
        #raise Exception('%s %s %s ' % (msg, location[0], location[1]))
        print(('%s %s %s ' % (msg, location[0], location[1])))
        token.lexer.skip(1)

    def _make_tok_location(self, token):
        return (token.lineno, self.find_tok_column(token))



    def t_COMMENT1(self, t):
        r"//.*\n"
        t.lexer.lineno += t.value.count('\n')-1
        # 返回一个NEWLINE
        t.lexer.skip(-1)
        #pass
        #return t

    def t_COMMENTN(self, t):
        r"/\*(.|\n)*?\*/"
        t.lexer.lineno += t.value.count('\n')
        #pass
        #return t

    def t_HASHKEY(self, t):
        r'[ \t]*\#'
        t.lexer.lineno += t.value.count('\n')
        #pass
        return t

    #t_ignore_COMMENT = r"//.*\n"
    #t_ignore_COMMENT1 = r"/\*(.|\n)*?\*/"
    #t_ignore_HASHKEY = r'[ \t]*\#.*\n'


    ##
    ## Regexes for use in tokens
    ##
    ##

    # valid C identifiers (K&R2: A.2.3), plus '$' (supported by some compilers)
    identifier = r'[a-zA-Z_$][0-9a-zA-Z_$]*'

    hex_prefix = '0[xX]'
    hex_digits = '[0-9a-fA-F]+'
    bin_prefix = '0[bB]'
    bin_digits = '[01]+'

    # integer constants (K&R2: A.2.5.1)
    integer_suffix_opt = r'(([uU]ll)|([uU]LL)|(ll[uU]?)|(LL[uU]?)|([uU][lL])|([lL][uU]?)|[uU])?'
    decimal_constant = '(0'+integer_suffix_opt+')|([1-9][0-9]*'+integer_suffix_opt+')'
    octal_constant = '0[0-7]*'+integer_suffix_opt
    hex_constant = hex_prefix+hex_digits+integer_suffix_opt
    bin_constant = bin_prefix+bin_digits+integer_suffix_opt

    bad_octal_constant = '0[0-7]*[89]'

    # character constants (K&R2: A.2.5.2)
    # Note: a-zA-Z and '.-~^_!=&;,' are allowed as escape chars to support #line
    # directives with Windows paths as filenames (..\..\dir\file)
    # For the same reason, decimal_escape allows all digit sequences. We want to
    # parse all correct code, even if it means to sometimes parse incorrect
    # code.
    #
    # The original regexes were taken verbatim from the C syntax definition,
    # and were later modified to avoid worst-case exponential running time.
    #
    #   simple_escape = r"""([a-zA-Z._~!=&\^\-\\?'"])"""
    #   decimal_escape = r"""(\d+)"""
    #   hex_escape = r"""(x[0-9a-fA-F]+)"""
    #   bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-7])"""
    #
    # The following modifications were made to avoid the ambiguity that allowed backtracking:
    # (https://github.com/eliben/pycparser/issues/61)
    #
    # - \x was removed from simple_escape, unless it was not followed by a hex digit, to avoid ambiguity with hex_escape.
    # - hex_escape allows one or more hex characters, but requires that the next character(if any) is not hex
    # - decimal_escape allows one or more decimal characters, but requires that the next character(if any) is not a decimal
    # - bad_escape does not allow any decimals (8-9), to avoid conflicting with the permissive decimal_escape.
    #
    # Without this change, python's `re` module would recursively try parsing each ambiguous escape sequence in multiple ways.
    # e.g. `\123` could be parsed as `\1`+`23`, `\12`+`3`, and `\123`.

    simple_escape = r"""([a-wyzA-Z._~!=&\^\-\\?'"]|x(?![0-9a-fA-F]))"""
    decimal_escape = r"""(\d+)(?!\d)"""
    hex_escape = r"""(x[0-9a-fA-F]+)(?![0-9a-fA-F])"""
    bad_escape = r"""([\\][^a-zA-Z._~^!=&\^\-\\?'"x0-9])"""

    escape_sequence = r"""(\\("""+simple_escape+'|'+decimal_escape+'|'+hex_escape+'))'

    # This complicated regex with lookahead might be slow for strings, so because all of the valid escapes (including \x) allowed
    # 0 or more non-escaped characters after the first character, simple_escape+decimal_escape+hex_escape got simplified to

    escape_sequence_start_in_string = r"""(\\[0-9a-zA-Z._~!=&\^\-\\?'"])"""

    cconst_char = r"""([^'\\\n]|"""+escape_sequence+')'
    char_const = "'"+cconst_char+"'"
    wchar_const = 'L'+char_const
    multicharacter_constant = "'"+cconst_char+"{2,4}'"
    unmatched_quote = "('"+cconst_char+"*\\n)|('"+cconst_char+"*$)"
    bad_char_const = r"""('"""+cconst_char+"""[^'\n]+')|('')|('"""+bad_escape+r"""[^'\n]*')"""

    # string literals (K&R2: A.2.6)
    string_char = r"""([^"\\\n]|"""+escape_sequence_start_in_string+')'
    string_literal = '"'+string_char+'*"'
    wstring_literal = 'L'+string_literal
    bad_string_literal = '"'+string_char+'*'+bad_escape+string_char+'*"'

    # floating constants (K&R2: A.2.5.3)
    exponent_part = r"""([eE][-+]?[0-9]+)"""
    fractional_constant = r"""([0-9]*\.[0-9]+)|([0-9]+\.)"""
    floating_constant = '(((('+fractional_constant+')'+exponent_part+'?)|([0-9]+'+exponent_part+'))[FfLl]?)'
    binary_exponent_part = r'''([pP][+-]?[0-9]+)'''
    hex_fractional_constant = '((('+hex_digits+r""")?\."""+hex_digits+')|('+hex_digits+r"""\.))"""
    hex_floating_constant = '('+hex_prefix+'('+hex_digits+'|'+hex_fractional_constant+')'+binary_exponent_part+'[FfLl]?)'



    ##
    ## Rules for the normal state
    ##
    #t_ignore = ' \t'
    #t_WS = r' \t'

    # Newlines
    def t_NEWLINE(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")
        t.value = '\n'
        return t

    def t_BLANK(self, t):
        r'\s+'
        t.lexer.lineno += t.value.count("\n")
        #return t
        pass


    # Operators
    t_PLUS              = r'\+'
    t_MINUS             = r'-'
    t_TIMES             = r'\*'
    t_DIVIDE            = r'/'
    t_MOD               = r'%'
    t_OR                = r'\|'
    t_AND               = r'&'
    t_NOT               = r'~'
    t_XOR               = r'\^'
    t_LSHIFT            = r'<<'
    t_RSHIFT            = r'>>'
    t_LOR               = r'\|\|'
    t_LAND              = r'&&'
    t_LNOT              = r'!'
    t_LT                = r'<'
    t_GT                = r'>'
    t_LE                = r'<='
    t_GE                = r'>='
    t_EQ                = r'=='
    t_NE                = r'!='


    t_ESC               = r'\\'


    # Assignment operators
    t_EQUALS            = r'='
    t_TIMESEQUAL        = r'\*='
    t_DIVEQUAL          = r'/='
    t_MODEQUAL          = r'%='
    t_PLUSEQUAL         = r'\+='
    t_MINUSEQUAL        = r'-='
    t_LSHIFTEQUAL       = r'<<='
    t_RSHIFTEQUAL       = r'>>='
    t_ANDEQUAL          = r'&='
    t_OREQUAL           = r'\|='
    t_XOREQUAL          = r'\^='

    # Increment/decrement
    t_PLUSPLUS          = r'\+\+'
    t_MINUSMINUS        = r'--'

    # ->
    t_ARROW             = r'->'

    # ?
    t_CONDOP            = r'\?'

    # Delimeters
    t_LPAREN            = r'\('
    t_RPAREN            = r'\)'
    t_LBRACKET          = r'\['
    t_RBRACKET          = r'\]'
    t_COMMA             = r','
    t_PERIOD            = r'\.'
    t_SEMI              = r';'
    t_COLON             = r':'
    t_ELLIPSIS          = r'\.\.\.'

    # Scope delimiters
    # To see why on_lbrace_func is needed, consider:
    #   typedef char TT;
    #   void foo(int TT) { TT = 10; }
    #   TT x = 5;
    # Outside the function, TT is a typedef, but inside (starting and ending
    # with the braces) it's a parameter.  The trouble begins with yacc's
    # lookahead token.  If we open a new scope in brace_open, then TT has
    # already been read and incorrectly interpreted as TYPEID.  So, we need
    # to open and close scopes from within the lexer.
    # Similar for the TT immediately outside the end of the function.
    #
    @TOKEN(r'\{')
    def t_LBRACE(self, t):
        return t
    @TOKEN(r'\}')
    def t_RBRACE(self, t):
        return t

    t_STRING_LITERAL = string_literal

    # The following floating and integer constants are defined as
    # functions to impose a strict order (otherwise, decimal
    # is placed before the others because its regex is longer,
    # and this is bad)
    #
    @TOKEN(floating_constant)
    def t_FLOAT_CONST(self, t):
        return t

    @TOKEN(hex_floating_constant)
    def t_HEX_FLOAT_CONST(self, t):
        return t

    @TOKEN(hex_constant)
    def t_INT_CONST_HEX(self, t):
        return t

    @TOKEN(bin_constant)
    def t_INT_CONST_BIN(self, t):
        return t

    @TOKEN(bad_octal_constant)
    def t_BAD_CONST_OCT(self, t):
        msg = "Invalid octal constant"
        self._error(msg, t)

    @TOKEN(octal_constant)
    def t_INT_CONST_OCT(self, t):
        return t

    @TOKEN(decimal_constant)
    def t_INT_CONST_DEC(self, t):
        return t

    # Must come before bad_char_const, to prevent it from
    # catching valid char constants as invalid
    #
    @TOKEN(multicharacter_constant)
    def t_INT_CONST_CHAR(self, t):
        return t

    @TOKEN(char_const)
    def t_CHAR_CONST(self, t):
        return t

    @TOKEN(wchar_const)
    def t_WCHAR_CONST(self, t):
        return t

    @TOKEN(unmatched_quote)
    def t_UNMATCHED_QUOTE(self, t):
        msg = "Unmatched '"
        self._error(msg, t)

    @TOKEN(bad_char_const)
    def t_BAD_CHAR_CONST(self, t):
        msg = "Invalid char constant %s" % t.value
        self._error(msg, t)

    @TOKEN(wstring_literal)
    def t_WSTRING_LITERAL(self, t):
        return t

    # unmatched string literals are caught by the preprocessor

    @TOKEN(bad_string_literal)
    def t_BAD_STRING_LITERAL(self, t):
        msg = "String contains invalid escape code"
        self._error(msg, t)

    @TOKEN(identifier)
    def t_ID(self, t):
        t.type = keyword_map.get(t.value, "ID")
        #if t.type == 'ID' and self.type_lookup_func(t.value):
        #    t.type = "TYPEID"
        return t

    def t_error(self, t):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)


def lex(string):
    lexer = ply.lex.lex(module=CTok(), reflags=re.UNICODE)
    lexer.input(string)
    a = []
    g_dict = globals()
    while 1:
        t = lexer.token()
        if t:
            if t.type == "ESC":
                next_t = lexer.token()
                # 转义符号后面是注释，则得不到换行符
                if next_t and next_t.lineno == t.lineno and next_t.type != "NEWLINE":
                    err_msg = ("ESC之后没有一个换行符 %s %s" % (t, next_t))
                    #raise Exception(err_msg)
                    logger.error(err_msg)
                # do nothing, 忽略 一个转义符 和 一个NEWLINE
            else:
                t.type = g_dict[t.type]
                a.append(t)
        else:
            return a

def unlex(tokens):
    "given a list of tokens (i.e. the output of lex() above), rebuild the original string"
    return ''.join(t.value for t in tokens)

