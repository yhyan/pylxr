#-----------------------------------------------------------------
# pycparser: __init__.py
#
# This package file exports some convenience functions for
# interacting with pycparser
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------
__all__ = ['c_lexer', 'c_parser', 'c_ast']
__version__ = '2.20'

import io

from .c_parser import CParser

def parse_file(filename,
               parser=None):
    """ Parse a C file using pycparser.

        filename:
            Name of the file you want to parse.

        parser:
            Optional parser object to be used instead of the default CParser

        When successful, an AST is returned. ParseError can be
        thrown if the file doesn't parse successfully.

        Errors from cpp will be printed out.
    """
    with io.open(filename) as f:
        text = f.read()

    if parser is None:
        parser = CParser()
    return parser.parse(text, filename)
