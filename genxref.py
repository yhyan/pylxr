#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import six
text_factory = str

import os
import subprocess

from files import Files
from models import Tree, File, Symbol, LangType, Definitions, Ref, init_db, create_session
from ctags import ctags



class Genxref(object):


    def __init__(self, config, tree):
        self.files = Files(tree)
        self.filestype = {}
        self.tree = tree
        self.commit_cnt = 0
        self.MAX_COMMIT = 1000        
        self.config = config



    def main(self, version):
        init_db(tree['name'], version)

        self.session = create_session(tree['name'], version)

        self.symid = Symbol.next_symid()

        self.init_tree()
        self.init_lang()
        self.pathname_to_obj = {}
        
        self.init_files('/', version)

        # ctags 符号
        self.symbols('/', version)
        # sym ref
        self.symref('/', version)


    def init_tree(self):
        from dbcache import treecache

        self.treeid = treecache.get_treeid(self.tree['name'], tree['version'])
        if self.treeid is None:
            self.treeid = Tree.query.get_treeid(tree['name'], tree['version'])
            assert self.treeid is not None
            treecache.load()


    def init_lang(self):
        from dbcache import langcache
        from simpleparse import parses

        self.parses = {}
        for k, v in parses.items():
            self.parses[k] = v(self.config, self.tree)

            assert LangType.query.get_or_create(k, '') is not None
            for desc in v.typemap.values():
                assert LangType.query.get_or_create(k, desc) is not None
        print(self.parses)
        langcache.load()
        

    def init_files(self, pathname, version):
        from dbcache import filecache

        _files = [(pathname, version)]
        
        while _files:
            pathname, version = _files.pop(0)

            if self.files.isdir(pathname, version):            
                dirs, files = self.files.getdir(pathname, version)
                for i in dirs + files:
                    _files.append((os.path.join(pathname, i), version))
            else:
                f = File(self.treeid, pathname)
                f.filetype = self.files.gettype(pathname, version)
                self.session.add(f)
                self.pathname_to_obj[pathname] = f
        self.session.commit()
        filecache.load(self.treeid)

    def symbols(self, pathname, version):
        from dbcache import langcache, symbolcache

        total_commit = 0
        _files = [(pathname, version)]
        while _files:
            pathname, version = _files.pop(0)
            if self.files.isdir(pathname, version):
                dirs, files = self.files.getdir(pathname, version)
                for i in dirs + files:
                    _files.append((os.path.join(pathname, i), version))
            else:
                o = self.pathname_to_obj[pathname]
                if o.filetype in self.parses and not o.has_indexed():
                    tags = ctags(self.files.toreal(pathname, version), o.filetype)
                    for tag in tags:
                        sym, line, lang_type, ext = tag
                        lang_typeid = langcache.get_typeid(o.filetype, self.parses[o.filetype].typemap[lang_type])
                        symbol_obj = Symbol(self.treeid, sym, self.symid)
                        defin = Definitions(self.symid, o.fileid, line, lang_typeid)
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
        print()
        print()
        symbolcache.load(self.treeid)
        

    def symref(self, pathname, version):
        from dbcache import symbolcache

        total_commit = 0
        _files = [(pathname, version)]
        while _files:
            pathname, version = _files.pop(0)
            if self.files.isdir(pathname, version):
                dirs, files = self.files.getdir(pathname, version)
                for i in dirs + files:
                    _files.append((os.path.join(pathname, i), version))
            else:
                o = self.pathname_to_obj[pathname]
                if o.filetype in self.parses and not o.has_refered():
                    with open(self.files.toreal(pathname, version), encoding="utf8", errors='ignore') as _fp:
                        _buf = _fp.read()
                    words = self.parses[o.filetype].get_idents(_buf)
                    for word, line in words:
                        _symid = symbolcache.get_symid(self.treeid, word)
                        if _symid is None:
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
    from conf import config, trees
    import sys

    treename = sys.argv[1]
    if len(sys.argv) >= 3:
        version = sys.argv[2]
    else:
        version = None

    tree = trees[treename]
    if version not in tree['versions']:
        version = tree['version']
    init_db(tree['name'], version)
    g = Genxref(config, tree)
    g.main(version)
    
