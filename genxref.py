#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import six
if six.PY2:
    reload(sys)
    sys.setdefaultencoding('utf8')
text_factory = str

import os
import subprocess

from files import Files
from index import Index
from lang import Lang
from simpleparse import *
from models import db, Tree, File, Symbol, LangType, Definitions, Ref
from ctags import ctags

from dbcache import treecache, langcache, filecache, symbolcache

class Genxref(object):

    def __init__(self, config, tree):
        self.files = Files(tree)
        self.filestype = {}
        self.tree = tree
        self.commit_cnt = 0
        self.MAX_COMMIT = 1000        
        self.config = config
        self.symid = Symbol.next_symid()


    def main(self, version):
        self.init_tree()
        self.init_lang()
        self.pathname_to_obj = {}
        
        self.init_files('/', version)

        # 建立swish
        # self.gensearch(version)
        # ctags 符号
        self.symbols('/', version)
        # sym ref
        self.symref('/', version)


    def init_tree(self):
        self.treeid = treecache.get_treeid(self.tree['name'], tree['version'])
        if self.treeid is None:
            self.treeid = Tree.query.get_treeid(tree['name'], tree['version'])
            assert self.treeid is not None
            treecache.load()


    def init_lang(self):
        self.parses = {}
        for k, v in parses.items():
            self.parses[k] = v(self.config, self.tree)

            assert LangType.query.get_or_create(k, '') is not None
            for desc in v.typemap.values():
                assert LangType.query.get_or_create(k, desc) is not None
        print(self.parses)
        langcache.load()
        

    def init_files(self, pathname, version):

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
                db.session.add(f)
                self.pathname_to_obj[pathname] = f
        db.session.commit()
        filecache.load(self.treeid)

        
    def feedswish(self, pathname, version, swish):
        if self.files.isdir(pathname, version):
            dirs, files = self.files.getdir(pathname, version)
            for i in dirs + files:
                self.feedswish(os.path.join(pathname, i),
                               version,
                               swish)
        else:
            _realfile = self.files.toreal(pathname, version)
            if _realfile in self.filestype:
                if self.filestype[_realfile] not in self.parses:
                    return

            # filelist.write('%s\n' % pathname)
            if self.files.getsize(pathname, version) > 0:
                fp = self.files.getfp(pathname, version)
                content = fp.read()
                swish_input = [
                    "Path-Name: %s\n" % pathname,
                    "Content-Length:  %s\n" % len(content),
                    "Document-Type: TXT\n",
                    "\n",
                    content]
            
                swish.stdin.write(''.join(swish_input))
                fp.close()
        
                
    def gensearch(self, version):
        index_file = "%s.%s.index" % (self.tree['name'], version)
        index_file = os.path.join(self.config['swishdirbase'], index_file)
        cmd = '%s -S prog -i stdin -v 1 -c %s -f %s' % (
            self.config['swishbin'],
            self.config['swishconf'],
            index_file)
        swish = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
        self.feedswish('.', version, swish)
        out, err = swish.communicate()


    def symbols(self, pathname, version):
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
                        db.session.add(symbol_obj)
                        db.session.add(defin)
                        self.symid += 1
                    o.set_indexed()
                    db.session.add(o)
                    total_commit += 1
                    if total_commit % 1000 == 0:
                        print(total_commit)
                        db.session.commit()
        db.session.commit()
        print()
        print()
        symbolcache.load(self.treeid)
        

    def symref(self, pathname, version):
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
                        db.session.add(ref)
                        total_commit += 1
                        if total_commit % 1000 == 0:
                            db.session.commit()
                            print(total_commit)
                    o.set_refered()
                    db.session.add(o)
                    total_commit += 1
                    if total_commit % 1000 == 0:
                        db.session.commit()
                        print(total_commit)

                    if total_commit % 10000 == 0:
                        print(total_commit)
        db.session.commit()
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
    g = Genxref(config, tree)
    g.main(version)
    
