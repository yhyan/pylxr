#!/usr/bin/env python
#conding=utf8
from cache import SimpleCache
from models import File, LangType, Tree, Symbol

class TreeCache(object):
    
    def __init__(self):
        self.cache = SimpleCache()
        self.load()
        
    def load(self):
        for i in Tree.query.all():
            treeid = i.id
            name = i.name
            version = i.version
            self.cache.set(treeid, (name, version))
            self.cache.set((name, version), treeid)

    def get_treeid(self, name, version):
        treeid = self.cache.get((name, version))
        if treeid is None:
            return None
        return treeid

    def get_name_version(self, treeid):
        rv = self.cache.get(treeid)
        if rv is None:
            return (None, None)
        return rv


class LangCache(object):
    def __init__(self):
        self.cache = SimpleCache()
        self.load()

    def load(self):
        for i in LangType.query.all():
            typeid = i.typeid
            lang = i.lang
            desc = i.desc
            self.cache.set(typeid, (lang, desc))
            self.cache.set((lang, desc), typeid)

    def get_typeid(self, lang, desc):
        typeid = self.cache.get((lang, desc))
        if typeid is None:
            print(lang, desc)
            return None
        return typeid

    def get_lang_desc(self, typeid):
        rv = self.cache.get(typeid)
        if rv is None:
            return None, None
        return rv

class FileCahe(object):

    def __init__(self, treeid=None):
        self.cache = SimpleCache()
        if treeid:
            self.load(treeid)
            
    def load(self, treeid):
        for i in File.query.filter(File.treeid==treeid).all():
            k = i.fileid
            v = (i.treeid, i.filename)
            self.cache.set(k, v)
            self.cache.set(v, k)
            
    def get_fileid(self, treeid, filename):
        rv = self.cache.get((treeid, filename))
        if rv is None:
            return None
        return rv

    def get_treeid_filename(self, fileid):
        rv = self.cache.get(fileid)
        if rv is None:
            return None, None
        return rv
    

class SymbolCache(object):
    def __init__(self, treeid=None):
        self.cache = SimpleCache()
        if treeid:
            self.load(treeid)
            
    def load(self, treeid):
        for i in Symbol.query.filter(Symbol.treeid==treeid).all():
            k = i.symid
            v = (i.treeid, i.symname)
            self.cache.set(k, v)
            self.cache.set(v, k)
            
    def get_symid(self, treeid, symname):
        rv = self.cache.get((treeid, symname))
        if rv is None:
            return None
        return rv
    
    def get_treeid_symname(self, symid):
        rv = self.cache.get(symid)
        if rv is None:
            return None, None
        return rv
    
    
treecache = TreeCache()        
langcache = LangCache()
filecache = FileCahe()
symbolcache = SymbolCache()

