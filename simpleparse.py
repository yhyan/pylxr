#!/usr/bin/env python

import os
import sys
import re
import string

from files import Files

from dbcache import symbolcache

__all__ = ['PythonParse', 'CPPParse', 'CParse', 'parses']

def find_escape_char(s, right, left):
    c = 0
    while right > left:
        if s[right] != '\\':
            break
        c += 1
        right -= 1
    if c % 2 == 0:
        return False
    return True


class SimpleParse(object):

    def __init__(self, project_name, project_path):
        self.project_name = project_name
        self.project_path = project_path

        self.files = Files(project_path)
        self.filename = ''
        self.buf = []
        self.pos = 0
        self.start = 0
        self.end = 0
        self.maxchar = 0

        self.frags = []

        self.open_re = re.compile("|".join(['(%s)' % i['open'] for i in self.spec]), re.M)


    def parse_file(self, filename):
        buf = self.files.get_txt(filename)
        self.parse(buf, filename)



    def get_line_html(self, line, width=4):
        line = '%04d' % line
        html = '''<a class='fline' name="%s">%s</a> ''' % (line, line)
        return html


    def _multilinetwist(self, frag, css):
        if css == 'string' or css == 'comment':
            frag = frag.replace("<", "&lt;").replace(">", "&gt;")

        ss = '''<span class="%s">%s</span>''' % (css, frag)
        ss = ss.replace("\n", '</span>\n<span class="%s">' % css)
        ss = ss.replace('<span class="%s"></span>' % css, '')
        return ss


    def get_include_link(self, word, path):
        html = '''<a class='include' href="/source/%s%s">%s</a>''' % (self.project_name, path, word)
        return html


    def get_ident_link(self, ident):
        html = '''<a class='fid' href="/ident/%s?_i=%s">%s</a>''' % (self.project_name, ident, ident)
        return html


    def get_reserved_link(self, word):
        if self.is_reserved(word):
            return '<span class="reserved">%s</span>' % word
        return word


    def is_ident(self, word):
        rv = symbolcache.get_symid(self.project_name, word)
        if rv is None:
            return False
        return True


    def is_reserved(self, word):
        return word in self.reserved

    def get_idents(self, buf):
        lines = buf.split('\n')
        line_no = 0
        kk = []
        for li in lines:
            line_no += 1
            if not li:
                continue
            ss = self.identdef.split(li)
            for i in ss:
                if not i:
                    continue
                if self.is_reserved(i):
                    continue
                kk.append((i, line_no))
        return kk


    def _parse_code(self, frag):
        raise Exception("Not Impl")

    def _is_package(self, word):
        return word != 'from' and word != 'import' and (word[0] == '.' or word[0] in string.ascii_letters)



    def parse(self, buf, filename=''):
        if filename:
            self.filename = filename

        self.buf = buf
        self.pos = 0
        self.start = 0
        self.end = 0
        self.maxchar = len(buf)

        self.frags = []

        while self.pos < self.maxchar:
            open_match = self.open_re.search(self.buf, self.pos, self.maxchar)
            if open_match:
                left, right = open_match.start(), open_match.end()
                if self.pos < left:
                    frag = self.buf[self.pos:left]
                    self.frags.append(('code', frag))

                match_groups = open_match.groups()
                i = 0
                while i < len(match_groups):
                    if match_groups[i]:
                        break
                    i += 1
                fragtype = self.spec[i]['type']
                close_re = self.spec[i]['close']
                close_left = self.buf.find(close_re, right, self.maxchar)
                # last line without newline
                if close_left < 0:
                    frag = self.buf[left:]
                    self.frags.append((fragtype, frag))
                    break
                close_right = close_left + len(close_re)
                if close_re == '"' or close_re == "'":
                    while find_escape_char(self.buf, close_left - 1, right - 1):
                        close_left = self.buf.find(close_re, close_right, self.maxchar)
                        # ERROR, break
                        if close_left < 0:
                            close_right = self.maxchar
                            print('ERROR.')
                            break
                        close_right = close_left + len(close_re)

                frag = self.buf[left:close_right]
                self.frags.append((fragtype, frag))
                self.pos = close_right
            else:
                frag = self.buf[self.pos:]
                self.frags.append(('code', frag))
                self.pos = self.maxchar

        _result = ''.join([i[1] for i in self.frags])
        assert _result == buf


    def _parse_include(self, frag):
        raise Exception("Not Impl")


    def out(self):
        head = '<pre class="filecontent">'
        tail = '</pre>'

        htmls = []
        for fragtype, frag in self.frags:
            if fragtype == 'comment':
                htmls.append(self._multilinetwist(frag, fragtype))
            elif fragtype == 'string':
                htmls.append(self._multilinetwist(frag, fragtype))
            elif fragtype == 'include':
                htmls.append(self._parse_include(frag))
            elif fragtype == 'code':
                htmls.append(self._parse_code(frag))
            else:
                htmls.append(self._parse_code(frag))
        htmls = [html for html in htmls]
        tt = ''.join(htmls).split("\n")
        while tt and (tt[-1] == '' or tt[-1] == '\n'):
            tt.pop()
        linewidth = max(len(str(len(tt))), 4)

        line = 1
        htmls = [self.get_line_html(line, linewidth)]
        for i in tt:
            htmls.append(i)
            htmls.append('\n')
            line += 1
            htmls.append(self.get_line_html(line, linewidth))
        htmls.insert(0, head)
        htmls.append(tail)
        return ''.join(htmls)


class PythonParse(SimpleParse):

    lang = 'python'
    blankre = re.compile('([a-zA-Z0-9_\.]+)')
    identdef = re.compile('([a-zA-Z]\w+)', re.M)
    reserved = ['and', 'as', 'assert', 'break', 'class', 'continue', 'def',
                'del', 'elif', 'else', 'except', 'exec', 'False', 'finally', 'for',
                'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None', 'not',
                'or', 'pass', 'print', 'raise', 'return', 'self', 'True', 'try',
                'while', 'with', 'yield']
    spec = [
        {'open': '#', 'close': '\n', 'type': 'comment'},
        {'open': '"""', 'close': '"""', 'type': 'string'},
        {'open': "'''", 'close': "'''", 'type': 'string'},
        {'open': '"', 'close': '"', 'type': 'string'},
        {'open': "'", 'close': "'", 'type': 'string'},
        {'open': "\\bimport\\b", 'close': '\n', 'type': 'include'},
        {'open': "\\bfrom\\b", 'close': '\n', 'type': 'include'}
    ]


    def __init__(self, project_name, project_path):
        super(PythonParse, self).__init__(project_name, project_path)

    def _parse_code(self, frag):
        ss = self.identdef.split(frag)
        kk = []
        for i in ss:
            if not i:
                continue
            if i == '<':
                i = "&lt;"
            elif i == '>':
                i = "&gt;"

            if self.is_reserved(i):
                kk.append(self.get_reserved_link(i))
            elif self.is_ident(i):
                kk.append(self.get_ident_link(i))
            else:
                kk.append(i)
        return ''.join(kk)



    def _parse_include(self, frag):
        ss = self.blankre.split(frag)
        kk = []

        for i in ss:
            if not i:
                continue
            if self.is_reserved(i):
                kk.append(self.get_reserved_link(i))
            elif self._is_package(i) and self.filename:
                if i.startswith(".."):
                    _dir = os.path.join(os.path.dirname(self.filename), '..')
                elif i.startswith("."):
                    _dir = os.path.dirname(self.filename)
                else:
                    _dir = '/'
                words = []
                for j in i.split("."):
                    words.append(j)
                    words.append('.')
                words.pop()
                for j in words:
                    if not j:
                        continue
                    if j == '.':
                        kk.append(j)
                    else:
                        if self.files.isdir(os.path.join(_dir, j)):
                            kk.append(self.get_include_link(j, os.path.join(_dir, j)))
                            _dir = os.path.join(_dir, j)
                        elif self.files.exists(os.path.join(_dir, j + ".py")):
                            kk.append(self.get_include_link(j, os.path.join(_dir, j + ".py")))
                        else:
                            kk.append(j)
            elif self.is_ident(i):
                kk.append(self.get_ident_link(i))
            else:
                kk.append(i)
        return ''.join(kk)


class CParse(SimpleParse):

    lang = 'c'
    blankre = re.compile('([\s\<\>"])', re.M)
    identdef = re.compile('([a-zA-Z_]\w+)', re.M)
    reserved = ['auto', 'break', 'case', 'char', 'const', 'continue',
                'default', 'do', 'double', 'else', 'enum', 'extern',
                'float', 'for', 'goto', 'if', 'int', 'long', 'register',
                'return', 'short', 'signed', 'sizeof', 'static', 'struct',
                'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile',
                'while', '#include', '#define', '#ifdef', '#else', '#elif',
                '#ifndef', '#endif', '#if', '#undef', '#error', '#pragma',
                '#warning', 'defined']
    spec = [
        {"open": "/\\*", "close": "*/", "type": "comment"},
        {"open": "//", "close": "\n", "type": "comment"},
        {"open": '"', "close": '"', "type": "string"},
        {"open": "'", "close": "'", "type": "string"},
        {"open": '#include', "close": '\n', "type": "include"}
    ]


    def _parse_include(self, frag):
        ss = self.blankre.split(frag)
        kk = []
        for i in ss:
            if i == '':
                continue
            ni = i.strip()
            if not ni:
                kk.append(i)
                continue

            if i == '<':
                i = "&lt;"
                kk.append(i)
            elif i == '>':
                i = "&gt;"
                kk.append(i)
            elif i == '"':
                kk.append(i)
            elif self.is_reserved(i):
                kk.append(self.get_reserved_link(i))
            elif self.filename:
                from models import get_engine

                eg = get_engine(self.project_name)
                sql = "select filename from src_file where filename like '%%%s' limit 1;" % i
                ret = eg.execute(sql)
                obj = ret.fetchone()
                if obj is None:
                    kk.append(i)
                else:
                    kk.append(self.get_include_link(i, obj[0]))
            elif self.is_ident(i):
                kk.append(self.get_ident_link(i))
            else:
                kk.append(i)
        return ''.join(kk)


    def _parse_code(self, frag):
        ss = self.identdef.split(frag)
        kk = []
        for i in ss:
            if not i:
                continue
            if i == '<':
                i = "&lt;"
            elif i == '>':
                i = "&gt;"

            if self.is_reserved(i):
                kk.append(self.get_reserved_link(i))
            elif self.is_ident(i):
                kk.append(self.get_ident_link(i))
            else:
                i = i.replace("<", "&lt;").replace(">", "&gt;")
                kk.append(i)
        return ''.join(kk)



class CPPParse(SimpleParse):

    lang = 'c++'
    blankre = re.compile('([\s\<\>\"])', re.M)
    identdef = re.compile('([a-zA-Z_]\w+)', re.M)
    reserved = ['and', 'and_eq', 'asm', 'auto', 'bitand', 'bitor', 'bool',
                'break', 'case', 'catch', 'char', 'class', 'const', 'const_cast',
                'continue', 'default', 'delete', 'do', 'double', 'dynamic_cast',
                'else', 'enum', 'explicit', 'export', 'extern', 'false', 'float',
                'for', 'friend', 'goto', 'if', 'inline', 'int', 'long', 'mutable',
                'namespace', 'new', 'not', 'not_eq', 'operator', 'or', 'or_eq',
                'private', 'protected', 'public', 'register', 'reinterpret_cast',
                'return', 'short', 'signed', 'sizeof', 'static', 'static_cast',
                'struct', 'switch', 'template', 'this', 'throw', 'true', 'try',
                'typedef', 'typeid', 'typename', 'union', 'unsigned', 'using',
                'virtual', 'void', 'volatile', 'wchar_t', 'while', 'xor', 'xor_eq',
                '#include', '#define', '#ifdef', '#else', '#elif', '#ifndef', '#endif',
                '#if', '#undef', '#error', '#pragma', '#warning', 'defined']

    spec = [
        {"open": "/\\*", "close": "*/", "type": "comment"},
        {"open": "//", "close": "\n", "type": "comment"},
        {"open": '"', "close": '"', "type": "string"},
        {"open": "'", "close": "'", "type": "string"},
        {"open": '#include', "close": '\n', "type": "include"}
    ]



    def _parse_include(self, frag):
        ss = self.blankre.split(frag)
        kk = []
        for i in ss:
            if i == '':
                continue
            if i == '<':
                i = "&lt;"
            elif i == '>':
                i = "&gt;"
            if self.is_reserved(i):
                kk.append(self.get_reserved_link(i))
            elif self.filename:
                _dir = os.path.dirname(self.filename)
                words = []
                for j in i.split("/"):
                    words.append(j)
                    words.append('/')
                words.pop()
                for j in words:
                    if not j:
                        continue
                    if j == '/':
                        kk.append(j)
                    else:
                        if self.files.isdir(os.path.join(_dir, j)):
                            kk.append(self.get_include_link(j, os.path.join(_dir, j)))
                            _dir = os.path.join(_dir, j)
                        elif self.files.exists(os.path.join(_dir, j)):
                            kk.append(self.get_include_link(j, os.path.join(_dir, j)))
                        else:
                            kk.append(j)
            elif self.is_ident(i):
                kk.append(self.get_ident_link(i))
            else:
                kk.append(i)
        return ''.join(kk)

    def _parse_code(self, frag):
        ss = self.identdef.split(frag)
        kk = []
        for i in ss:
            if not i:
                continue

            if i == '<':
                i = "&lt;"
            elif i == '>':
                i = "&gt;"

            if self.is_reserved(i):
                kk.append(self.get_reserved_link(i))
            elif self.is_ident(i):
                kk.append(self.get_ident_link(i))
            else:
                i = i.replace("<", "&lt;").replace(">", "&gt;")
                kk.append(i)
        return ''.join(kk)


class GOParse(SimpleParse):
    lang = 'go'
    blankre = re.compile('([\s\<\>"])', re.M)
    identdef = re.compile('([a-zA-Z_]\w+)', re.M)
    reserved = ['auto', 'break', 'case', 'char', 'const', 'continue',
                'default', 'do', 'double', 'else', 'enum', 'extern',
                'float', 'for', 'goto', 'if', 'int', 'long', 'register',
                'return', 'short', 'signed', 'sizeof', 'static', 'struct',
                'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile',
                'while', '#include', '#define', '#ifdef', '#else', '#elif',
                '#ifndef', '#endif', '#if', '#undef', '#error', '#pragma',
                '#warning', 'defined']
    spec = [
        {"open": "/\\*", "close": "*/", "type": "comment"},
        {"open": "//", "close": "\n", "type": "comment"},
        {"open": '"', "close": '"', "type": "string"},
        {"open": "'", "close": "'", "type": "string"},
        # {"open": '#pa', "close": '\n', "type": "include"}
    ]



    def _parse_code(self, frag):
        ss = self.identdef.split(frag)
        kk = []
        for i in ss:
            if not i:
                continue
            if i == '<':
                i = "&lt;"
            elif i == '>':
                i = "&gt;"

            if self.is_reserved(i):
                kk.append(self.get_reserved_link(i))
            elif self.is_ident(i):
                kk.append(self.get_ident_link(i))
            else:
                i = i.replace("<", "&lt;").replace(">", "&gt;")
                kk.append(i)
        return ''.join(kk)


parses = {
    PythonParse.lang: PythonParse,
    CParse.lang: CParse,
    CPPParse.lang: CPPParse,
    GOParse.lang: GOParse,

}



if __name__ == "__main__":
    from conf import trees
    for filename in sys.argv[1:]:
        fp = open(filename)
        buf = fp.read()
        fp.close()
        parse = PythonParse(trees['redispy'])
        parse.parse(buf)








