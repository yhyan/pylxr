#!/usr/bin/env python
#conding=utf8
from cache import SimpleCache
from models import File, Symbol, SwitchEngine, get_engine

class FileCahe(object):

    def __init__(self):
        self.cache_dict = {}
            
    def load(self, project_name, project_version):
        project_key = '%s.%s' % (project_name, project_version)
        if project_key in self.cache_dict:
            return self.cache_dict[project_key]

        cache = SimpleCache()
        with SwitchEngine(get_engine(project_name, project_version)):
            for i in File.query.all():
                k = i.fileid
                v = i.filename
                cache.set(k, v)
                cache.set(v, k)
        self.cache_dict[project_key] = cache
        return cache
            
    def get_fileid(self, project_name, project_version, filename):
        cache = self.load(project_name, project_version)
        rv = cache.get(filename)
        if rv is None:
            return None
        return rv

    def get_filename(self, project_name, project_version, fileid):
        cache = self.load(project_name, project_version)
        rv = cache.get(fileid)
        if rv is None:
            return None, None
        return rv
    

class SymbolCache(object):
    def __init__(self):
        self.cache_dict = {}
            
    def load(self, project_name, project_version):
        project_key = '%s.%s' % (project_name, project_version)
        if project_key in self.cache_dict:
            return self.cache_dict[project_key]

        cache = SimpleCache()
        with SwitchEngine(get_engine(project_name, project_version)):

            for i in Symbol.query.all():
                k = i.symid
                v = i.symname
                cache.set(k, v)
                cache.set(v, k)
        self.cache_dict[project_key] = cache
        return cache

            
    def get_symid(self, project_name, project_version, symname):
        cache = self.load(project_name, project_version)
        rv = cache.get(symname)
        if rv is None:
            return None
        return rv
    
    def get_symname(self, project_name, project_version, symid):
        cache = self.load(project_name, project_version)
        rv = cache.get(symid)
        if rv is None:
            return None, None
        return rv

filecache = FileCahe()
symbolcache = SymbolCache()

