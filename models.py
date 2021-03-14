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

class SwitchEngine(object):

    def __init__(self, eg):
        self.eg = eg
        self.origin_eg = None

    def __enter__(self):
        self.origin_eg = base_model.metadata.bind
        base_model.metadata.bind = self.eg

    def __exit__(self, exc_type, exc_val, exc_tb):
        base_model.metadata.bind = self.origin_eg
        self.origin_eg = None




import os
from conf import index_dir

_eg_cache = {}

def get_engine(project_name):
    global _eg_cache

    db_name = '%s.sqlite3' % (project_name)
    db_path = os.path.join(index_dir, db_name)
    db_uri = 'sqlite:///' + db_path
    eg = create_engine(db_uri, echo=False)
    if not os.path.exists(db_path):
        _eg_cache[db_name] = eg
    return eg

def create_session(project_name):
    session = Session(autocommit=False, autoflush=False,
                     expire_on_commit=False,
                     bind=get_engine(project_name))
    return session

def init_db(project_name):
    eg = get_engine(project_name)
    base_model.metadata.bind = eg
    base_model.metadata.drop_all()
    base_model.metadata.create_all()



def create_session_from_bind(bind):
    session = Session(autocommit=False, autoflush=False,
                     expire_on_commit=False,
                     bind=bind)
    return session


        
    
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



class SymbolQuery(BaseQuery):

    @cached
    def get_by_name(self, name):
        return self.filter(Symbol.symname==name).first()

    @cached
    def get_symid(self, name):
        rv = self.filter(Symbol.symname==name).first()
        if rv is None:
            return None
        return rv.symid
    

    @cached
    def get_or_create(self, name):
        rv = self.filter(Symbol.symname==name).first()
        if rv is None:
            rv = Symbol(name)
            self.session.add(rv)
            self.session.commit()
        return rv
    

from sqlalchemy.sql import func
    
class Symbol(base_model):
    __tablename__ = 'src_symbol'

    query_class = SymbolQuery
    
    symid = Column(Integer, nullable=False, primary_key=True)
    symname = Column(String(255), nullable=False)

    def __init__(self, symname, symid=1):
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
    def get_or_create(self, filename):
        rv = self.filter(File.filename==filename).first()
        if rv is None:
            rv = File(filename)
            self.session.add(rv)
            self.session.commit()
        return rv

    
class File(base_model):
    __tablename__ = 'src_file'

    query_class = FileQuery
    
    fileid = Column(Integer, nullable=False, primary_key=True, autoincrement=True)

    filename = Column(String(256), nullable=False)
    filetype = Column(String(16), nullable=True)
    # 1 表是index 2 表示ref
    status = Column(Integer, nullable=False, default=0)
    indexed_at = Column(DateTime, nullable=True)
    refered_at = Column(DateTime, nullable=True)
    
    def __init__(self, filename):
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

