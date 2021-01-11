#!/usr/bin/env python
#-*- coding:utf-8 -*-



from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Query

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

import re
import uuid
import functools
from functools import partial
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import attributes, object_mapper
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.util import to_list
from sqlalchemy.orm.exc import UnmappedClassError


from cache import cached




class _QueryProperty(object):

    def __init__(self, model):
        self.model = model

    def __get__(self, obj, type):
        try:
            mapper = orm.class_mapper(type)
            if mapper:
                session = create_session_from_bind(self.model.metadata.bind)
                return type.query_class(mapper, session=session)
        except UnmappedClassError:
            return None


class BaseQuery(orm.Query):
    """The default query object used for models.  This can be subclassed and
    replaced for individual models by setting the :attr:`~Model.query_class`
    attribute.  This is a subclass of a standard SQLAlchemy
    :class:`~sqlalchemy.orm.query.Query` class and has all the methods of a
    standard query as well.
    """
    def get_or_404(self, ident):
        """Like :meth:`get` but aborts with 404 if not found instead of
        returning `None`.
        """
        rv = self.get(ident)
        return rv
    
    def first_or_404(self):
        """Like :meth:`first` but aborts with 404 if not found instead of
        returning `None`.
        """
        rv = self.first()
        return rv



class Model(object):
    """Baseclass for custom user models."""

    #: the query class used.  The :attr:`query` attribute is an instance
    #: of this class.  By default a :class:`BaseQuery` is used.
    query_class = BaseQuery

    #: an instance of :attr:`query_class`.  Can be used to query the
    #: database for instances of this model.
    query = None
    
    PER_PAGE = None


base_model = declarative_base(cls=Model, name='Model')

base_model.query = _QueryProperty(base_model)






import os
from conf import index_dir

_eg_cache = {}

def get_engine(project_name, project_version):
    global _eg_cache

    db_name = '%s.%s.sqlite3' % (project_name, project_version)
    db_path = os.path.join(index_dir, db_name)
    db_uri = 'sqlite:///' + db_path
    eg = create_engine(db_uri, echo=False)
    if not os.path.exists(db_path):
        _eg_cache[db_name] = eg
    return eg

def create_session(project_name, project_version):
    session = Session(autocommit=False, autoflush=False,
                     expire_on_commit=False,
                     bind=get_engine(project_name, project_version))
    return session

def init_db(project_name, project_version):
    eg = get_engine(project_name, project_version)
    base_model.metadata.bind = eg
    base_model.metadata.drop_all()
    base_model.metadata.create_all()

_current_project_name = None
_current_project_version = None

def change_session(project_name, project_version):
    global _current_project_name, _current_project_version

    if project_name != _current_project_name or project_version != _current_project_version:
        eg = get_engine(project_name, project_version)
        base_model.metadata.bind = eg

        _current_project_name = project_name
        _current_project_version = _current_project_version

        from dbcache import treecache, filecache, symbolcache

        tree_id = treecache.get_treeid(project_name, project_version)
        symbolcache.load(tree_id)
        filecache.load(tree_id)


def create_session_from_bind(bind):
    session = Session(autocommit=False, autoflush=False,
                     expire_on_commit=False,
                     bind=bind)
    return session


class TreeQuery(BaseQuery):

    @cached
    def get_treeid(self, name, version):
        rv = self.filter(Tree.name==name, Tree.version==version).first()
        if rv is None:
            rv = Tree(name, version)
            session = create_session(name, version)
            session.add(rv)
            session.commit()
        return rv.id
    

class Tree(base_model):
    __tablename__ = 'src_tree'

    query_class = TreeQuery
    
    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    name = Column(String(64), nullable=False)
    version = Column(String(64), nullable=False)

    def __init__(self, name, version):
        self.name = name
        self.version = version
        
    
class Definitions(base_model):
    __tablename__ = 'src_definitions'

    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    symid = Column(Integer, nullable=False)
    fileid = Column(Integer, nullable=False)
    line = Column(Integer, nullable=False)
    typeid = Column(Integer, nullable=False)
    
    def __init__(self, symid, fileid, line, typeid):
        self.symid = symid
        self.fileid = fileid
        self.line = line
        self.typeid = typeid


class LangTypeQuery(BaseQuery):

    @cached
    def get_or_create(self, lang, desc):
        rv = self.filter(LangType.lang == lang, LangType.desc == desc).first()
        if rv is None:
            rv = LangType(lang, desc)
            self.session.add(rv)
            self.session.commit()
        return rv
    
        
class LangType(base_model):
    __tablename__ = 'src_langtype'

    query_class = LangTypeQuery
    
    typeid = Column(Integer, nullable=False, primary_key=True, autoincrement=True)
    lang = Column(String(64), nullable=False)
    desc = Column(String(128), nullable=False, default='')

    def __init__(self, lang, desc):
        self.lang = lang
        self.desc = desc


class SymbolQuery(BaseQuery):

    @cached
    def get_by_name(self, treeid, name):
        return self.filter(Symbol.symname==name, Symbol.treeid==treeid).first()

    @cached
    def get_symid(self, treeid, name):
        rv = self.filter(Symbol.symname==name, Symbol.treeid==treeid).first()
        if rv is None:
            return None
        return rv.symid
    

    @cached
    def get_or_create(self, treeid, name):
        rv = self.filter(Symbol.symname==name, Symbol.treeid==treeid).first()
        if rv is None:
            rv = Symbol(treeid, name)
            self.session.add(rv)
            self.session.commit()
        return rv
    

from sqlalchemy.sql import func
    
class Symbol(base_model):
    __tablename__ = 'src_symbol'

    query_class = SymbolQuery
    
    symid = Column(Integer, nullable=False, primary_key=True)
    treeid = Column(Integer, nullable=False)
    symname = Column(String(255), nullable=False)

    def __init__(self, treeid, symname, symid=1):
        self.treeid = treeid
        self.symname = symname
        self.symid = symid 

    @classmethod
    def next_symid(cls):
        session = create_session_from_bind(cls.metadata.bind)
        qry = session.query(func.max(cls.symid).label('max_symid')).first()
        if qry and qry.max_symid:
            return qry.max_symid + 1
        return 1
    


class FileQuery(BaseQuery):

    @cached
    def get_or_create(self, treeid, filename):
        rv = self.filter(File.treeid==treeid, File.filename==filename).first()
        if rv is None:
            rv = File(treeid, filename)
            self.session.add(rv)
            self.session.commit()
        return rv

    
class File(base_model):
    __tablename__ = 'src_file'

    query_class = FileQuery
    
    fileid = Column(Integer, nullable=False, primary_key=True, autoincrement=True)

    treeid = Column(Integer, nullable=False)
    filename = Column(String(256), nullable=False)
    filetype = Column(String(16), nullable=True)
    # 1 表是index 2 表示ref
    status = Column(Integer, nullable=False, default=0)
    indexed_at = Column(DateTime, nullable=True)
    refered_at = Column(DateTime, nullable=True)
    
    def __init__(self, treeid, filename):
        self.treeid = treeid
        self.filename = filename

    def set_indexed(self):
        self.status = self.status | 1

    def set_refered(self):
        self.status = self.status | 2
        
    def has_indexed(self):
        return self.status & 1

    def has_refered(self):
        return self.status & 2
    
        
        
class Ref(base_model):
    __tablename__ = 'src_ref'

    
    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)    
    symid = Column(Integer, nullable=False)
    fileid = Column(Integer, nullable=False)
    line = Column(Integer, nullable=False)

    def __init__(self, symid, fileid, line):
        self.symid = symid
        self.fileid = fileid
        self.line = line


if __name__ == "__main__":
    eg = get_engine('test', '1.0')
    base_model.metadata.bind = eg
    base_model.metadata.drop_all()
    base_model.metadata.create_all()
