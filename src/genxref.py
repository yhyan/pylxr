#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import six
text_factory = str

import os
import time
import json

from files import Files
from models import File, Symbol, Definitions, Ref, init_db, create_session
from tags.base import find_tags

import logging
from log import configure_logging

configure_logging()

logger = logging.getLogger('fordeploy')


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

        self.track_info = {}


    def main(self):

        self.session = create_session(self.project_name)

        self.symid = 1 # Symbol.next_symid()

        from simpleparse import parses

        self.parses = {}
        for k, v in parses.items():
            self.parses[k] = v(self.project_name, self.project_path)



        self.pathname_to_obj = {}
        
        self.init_files(self.start_path)

        t0 = time.time()
        # ctags 符号
        self.symbols(self.start_path)
        t1 = time.time()

        # sym ref
        self.symref(self.start_path)
        t2 = time.time()
        self.track_info['t1'] = int(t1-t0)
        self.track_info['t2'] = int(t2-t1)
        return self.track_info



    def init_files(self, pathname):

        _files = [pathname]
        file_count = 0
        line_count = 0
        while _files:
            pathname = _files.pop(0)

            if self.files.isdir(pathname):
                dirs, files = self.files.getdir(pathname)
                for i in dirs + files:
                    _files.append(os.path.join(pathname, i))
            else:
                f = File(pathname)
                cnt = self.files.getlinecount(pathname)
                f.filetype = self.files.gettype(pathname)
                f.linecount = cnt
                self.session.add(f)
                file_count += 1
                line_count += cnt
                self.pathname_to_obj[pathname] = f
        self.session.commit()

        self.track_info['file_count'] = file_count
        self.track_info['line_count'] = line_count


    def symbols(self, pathname):

        total_commit = 0
        _files = [pathname]
        exist_syms = {}
        while _files:
            pathname = _files.pop(0)
            if self.files.isdir(pathname):
                dirs, files = self.files.getdir(pathname)
                for i in dirs + files:
                    _files.append(os.path.join(pathname, i))
            else:
                o = self.pathname_to_obj[pathname]
                if o.filetype in self.parses and not o.has_indexed():
                    logger.info('find tags: %s' % pathname)
                    tags = find_tags(self.files.toreal(pathname), o.filetype)
                    for tag in tags:
                        sym, line, lang_typeid = tag

                        if sym in exist_syms:
                            sym_id = exist_syms[sym]
                        else:
                            symbol_obj = Symbol(sym, self.symid)
                            sym_id = self.symid
                            exist_syms[sym] = sym_id
                            self.symid += 1
                            self.session.add(symbol_obj)

                        defin = Definitions(sym_id, o.fileid, line, lang_typeid)
                        self.sym_filetype[sym_id] = o.filetype
                        self.session.add(defin)

                        total_commit += 1
                        if total_commit % 1000 == 0:
                            self.session.commit()

                    o.set_indexed()
                    self.session.add(o)
                    logger.info('find %s tags: %s' % (len(tags), pathname))

        self.session.commit()
        self.track_info['total_symbol'] = total_commit
        logger.info('finish tags, total = %s' % total_commit)

        

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
                        if o.filetype == 'asm':
                            if word[0] == '_':
                                # 汇编调用C语言函数
                                _symid = symbolcache.get_symid(self.project_name, word[1:])
                            else:
                                _symid = symbolcache.get_symid(self.project_name, word)
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
        self.track_info['total_ref'] = total_commit
        print()


                    
if __name__ == "__main__":
    from conf import trees

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
    track_info = g.main()

    from conf import index_dir

    jsonfile = os.path.join(index_dir, 'trackinfo.json')
    if not os.path.exists(jsonfile):
        data = {}
    else:
        with open(jsonfile, 'r') as fp:
            data = json.loads(fp.read())
    data[project_name] = track_info
    with open(jsonfile, 'w') as fp:
        fp.write(json.dumps(data, indent=True))




