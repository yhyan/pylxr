#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import six
text_factory = str

import os

from files import Files
from models import File, Symbol, Definitions, Ref, init_db, create_session
from tags.base import find_tags

class Genxref(object):


    def __init__(self, project_name, project_path, start_path='/'):
        self.files = Files(project_path)
        self.filestype = {}
        self.project_name = project_name
        self.project_path = project_path
        self.commit_cnt = 0
        self.MAX_COMMIT = 1000        

        self.start_path = start_path

        self.sym_filetype = {}


    def main(self):

        self.session = create_session(self.project_name)

        self.symid = 1 # Symbol.next_symid()



        from simpleparse import parses

        self.parses = {}
        for k, v in parses.items():
            self.parses[k] = v(self.project_name, self.project_path)

        print(self.parses)

        self.pathname_to_obj = {}
        
        self.init_files(self.start_path)

        # ctags 符号
        self.symbols(self.start_path)
        # sym ref
        self.symref(self.start_path)



    def init_files(self, pathname):

        _files = [pathname]
        
        while _files:
            pathname = _files.pop(0)

            if self.files.isdir(pathname):
                dirs, files = self.files.getdir(pathname)
                for i in dirs + files:
                    _files.append(os.path.join(pathname, i))
            else:
                f = File(pathname)
                f.filetype = self.files.gettype(pathname)
                self.session.add(f)
                self.pathname_to_obj[pathname] = f
        self.session.commit()


    def symbols(self, pathname):

        total_commit = 0
        _files = [pathname]
        while _files:
            pathname = _files.pop(0)
            if self.files.isdir(pathname):
                dirs, files = self.files.getdir(pathname)
                for i in dirs + files:
                    _files.append(os.path.join(pathname, i))
            else:
                o = self.pathname_to_obj[pathname]
                if o.filetype in self.parses and not o.has_indexed():
                    tags = find_tags(self.files.toreal(pathname), o.filetype)
                    for tag in tags:
                        sym, line, lang_typeid = tag
                        symbol_obj = Symbol(sym, self.symid)
                        defin = Definitions(self.symid, o.fileid, line, lang_typeid)
                        self.sym_filetype[self.symid] = o.filetype
                        self.session.add(symbol_obj)
                        self.session.add(defin)
                        self.symid += 1
                    o.set_indexed()
                    self.session.add(o)
                    total_commit += 1
                    if total_commit % 1000 == 0:
                        print(total_commit)
                        self.session.commit()
        self.session.commit()
        print(total_commit)
        print()

        

    def symref(self, pathname):
        from dbcache import symbolcache

        total_commit = 0
        _files = [pathname]
        while _files:
            pathname = _files.pop(0)
            if self.files.isdir(pathname):
                dirs, files = self.files.getdir(pathname)
                for i in dirs + files:
                    _files.append(os.path.join(pathname, i))
            else:
                o = self.pathname_to_obj[pathname]
                if o.filetype in self.parses and not o.has_refered():
                    with open(self.files.toreal(pathname), encoding="utf8", errors='ignore') as _fp:
                        _buf = _fp.read()
                    words = self.parses[o.filetype].get_idents(_buf)
                    for word, line in words:
                        if o.filetype == 'asm' and word[0] == '_':
                            # 汇编调用C语言函数
                            _symid = symbolcache.get_symid(self.project_name, word[1:])
                            if _symid is None:
                                continue
                        else:
                            _symid = symbolcache.get_symid(self.project_name, word)
                            if _symid is None:
                                continue

                            if not self.files.is_same_filetype(o.filetype, self.sym_filetype.get(_symid)):
                                continue

                        ref = Ref(_symid, o.fileid, line)
                        self.session.add(ref)
                        total_commit += 1
                        if total_commit % 1000 == 0:
                            self.session.commit()
                            print(total_commit)
                    o.set_refered()
                    self.session.add(o)
                    total_commit += 1
                    if total_commit % 1000 == 0:
                        self.session.commit()
                        print(total_commit)

                    if total_commit % 10000 == 0:
                        print(total_commit)
        self.session.commit()
        print()


                    
if __name__ == "__main__":
    from conf import  trees
    import sys

    project_name = sys.argv[1]
    if project_name not in trees:
        print('%s not in trees.' % project_name)
        sys.exit(0)

    if len(sys.argv) >= 3:
        # for debug single file
        start_path = sys.argv[2]
    else:
        start_path = '/'

    project_path = trees[project_name]
    init_db(project_name)
    g = Genxref(project_name, project_path, start_path)
    g.main()

