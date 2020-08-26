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
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.orm.interfaces import MapperExtension, SessionExtension, \
     EXT_CONTINUE
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.util import to_list

from signals import Namespace

from cache import cached

_camelcase_re = re.compile(r'([A-Z]+)(?=[a-z0-9])')

_signals = Namespace()

models_committed = _signals.signal('models-committed')
before_models_committed = _signals.signal('before-models-committed')

def _make_table(db):
    def _make_table(*args, **kwargs):
        if len(args) > 1 and isinstance(args[1], db.Column):
            args = (args[0], db.metadata) + args[1:]
        return sqlalchemy.Table(*args, **kwargs)
    return _make_table


def _set_default_query_class(d):
    if 'query_class' not in d:
        d['query_class'] = BaseQuery


def _wrap_with_default_query_class(fn):
    @functools.wraps(fn)
    def newfn(*args, **kwargs):
        _set_default_query_class(kwargs)
        if "backref" in kwargs:
            backref = kwargs['backref']
            if isinstance(backref, basestring):
                backref = (backref, {})
            _set_default_query_class(backref[1])
        return fn(*args, **kwargs)
    return newfn


def _defines_primary_key(d):
    """Figures out if the given dictonary defines a primary key column."""
    return any(v.primary_key for k, v in d.items()
               if isinstance(v, sqlalchemy.Column))


def _include_sqlalchemy(obj):
    for module in sqlalchemy, sqlalchemy.orm:
        for key in module.__all__:
            if not hasattr(obj, key):
                setattr(obj, key, getattr(module, key))
    # Note: obj.Table does not attempt to be a SQLAlchemy Table class.
    obj.Table = _make_table(obj)
    obj.mapper = signalling_mapper
    obj.relationship = _wrap_with_default_query_class(obj.relationship)
    obj.relation = _wrap_with_default_query_class(obj.relation)
    obj.dynamic_loader = _wrap_with_default_query_class(obj.dynamic_loader)


class _BoundDeclarativeMeta(DeclarativeMeta):

    def __new__(cls, name, bases, d):
        tablename = d.get('__tablename__')

        # generate a table name automatically if it's missing and the
        # class dictionary declares a primary key.  We cannot always
        # attach a primary key to support model inheritance that does
        # not use joins.  We also don't want a table name if a whole
        # table is defined
        if not tablename and not d.get('__table__') and \
           _defines_primary_key(d):
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()
            d['__tablename__'] = _camelcase_re.sub(_join, name).lstrip('_')

        return DeclarativeMeta.__new__(cls, name, bases, d)

    def __init__(self, name, bases, d):
        bind_key = d.pop('__bind_key__', None)
        DeclarativeMeta.__init__(self, name, bases, d)
        if bind_key is not None:
            self.__table__.info['bind_key'] = bind_key


class _SignallingSession(Session):

    def __init__(self, db, autocommit=False, autoflush=False, **options):
        self.sender = db.sender
        self._model_changes = {}
        Session.__init__(self, autocommit=autocommit, autoflush=autoflush,
                         expire_on_commit=False,
                         extension=db.session_extensions,
                         bind=db.engine, **options)


class _QueryProperty(object):

    def __init__(self, sa):
        self.sa = sa

    def __get__(self, obj, type):
        try:
            mapper = orm.class_mapper(type)
            if mapper:
                return type.query_class(mapper, session=self.sa.session())
        except UnmappedClassError:
            return None


class _SignalTrackingMapperExtension(MapperExtension):

    def after_delete(self, mapper, connection, instance):
        return self._record(mapper, instance, 'delete')

    def after_insert(self, mapper, connection, instance):
        return self._record(mapper, instance, 'insert')

    def after_update(self, mapper, connection, instance):
        return self._record(mapper, instance, 'update')

    def _record(self, mapper, model, operation):
        pk = tuple(mapper.primary_key_from_instance(model))
        #orm.object_session(model)._model_changes[pk] = (model, operation)
        changes = {}

        for prop in object_mapper(model).iterate_properties:
            if not isinstance(prop, RelationshipProperty):
                try:
                    history = attributes.get_history(model, prop.key)
                except:
                    continue

                added, unchanged, deleted = history

                newvalue = added[0] if added else None

                if operation=='delete':
                    oldvalue = unchanged[0] if unchanged else None
                else:
                    oldvalue = deleted[0] if deleted else None

                if newvalue or oldvalue:
                    changes[prop.key] = (oldvalue, newvalue)

        orm.object_session(model)._model_changes[pk] = (model.__tablename__, pk[0], changes, operation)
        return EXT_CONTINUE


class _SignallingSessionExtension(SessionExtension):

    def before_commit(self, session):
        d = session._model_changes
        if d:
            before_models_committed.send(session.sender, changes=d.values())
        return EXT_CONTINUE

    def after_commit(self, session):
        d = session._model_changes
        if d:
            models_committed.send(session.sender, changes=d.values())
            d.clear()
        return EXT_CONTINUE

    def after_rollback(self, session):
        session._model_changes.clear()
        return EXT_CONTINUE


def signalling_mapper(*args, **kwargs):
    """Replacement for mapper that injects some extra extensions"""
    extensions = to_list(kwargs.pop('extension', None), [])
    extensions.append(_SignalTrackingMapperExtension())
    kwargs['extension'] = extensions
    return sqlalchemy.orm.mapper(*args, **kwargs)


class _ModelTableNameDescriptor(object):

    def __get__(self, obj, type):
        tablename = type.__dict__.get('__tablename__')
        if not tablename:
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()
            tablename = _camelcase_re.sub(_join, type.__name__).lstrip('_')
            setattr(type, '__tablename__', tablename)
        return tablename



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
    

class SQLAlchemy(object):
    """
    Example:
        db = SQLAlchemy("sqlite:///test.db", True)
        
        class User(db.Model):
            username = db.Column(db.String(16), unique=True, nullable=False, index=True)
            password = db.Column(db.String(30), nullable=False)
            email = db.Column(db.String(30), nullable=False)

        >>> user1 = User.query.filter(User.username=='name').first()
        >>> user2 = User.query.get(1)
        >>> user_list = User.query.filter(db.and_(User.username=='test1', User.email.ilike('%@gmail.com'))).limit(10)
        
    """
    def __init__(self, engine_url='', echo=False, pool_recycle=7200, pool_size=10,
                 session_extensions=None, session_options=None):
        # create signals sender
        self.sender = str(uuid.uuid4())

        self.session_extensions = to_list(session_extensions, []) + [_SignallingSessionExtension()]
                                  
        self.session = self.create_scoped_session(session_options)
        self.Model = self.make_declarative_base()

        if engine_url != '':
            self.engine = sqlalchemy.create_engine(engine_url, echo=echo) #, pool_recycle=pool_recycle, pool_size=pool_size)
        else:
            self.engine = None

        _include_sqlalchemy(self)

    def create_scoped_session(self, options=None):
        """Helper factory method that creates a scoped session."""
        if options is None:
            options = {}
        return orm.scoped_session(partial(_SignallingSession, self, **options))

    def make_declarative_base(self):
        """Creates the declarative base."""
        base = declarative_base(cls=Model, name='Model',
                                mapper=signalling_mapper,
                                metaclass=_BoundDeclarativeMeta)
        base.query = _QueryProperty(self)
        return base

    def create_all(self):
        """Creates all tables."""
        if self.engine is not None:
            self.Model.metadata.create_all(bind=self.engine)
        else:
            raise Exception('engine is none')

    def drop_all(self):
        """Drops all tables."""
        if self.engine is not None:
            self.Model.metadata.drop_all(bind=self.engine)
        else:
            raise Exception('engine is none')



import os
from conf import data_dir
DBURI = 'sqlite:///' + os.path.join(data_dir, 'lxr.sqlite3')

db = SQLAlchemy(DBURI)
        
class TreeQuery(BaseQuery):

    @cached
    def get_treeid(self, name, version):
        rv = self.filter(Tree.name==name, Tree.version==version).first()
        if rv is None:
            rv = Tree(name, version)
            db.session.add(rv)
            db.session.commit()
        return rv.id
    

class Tree(db.Model):
    __tablename__ = 'src_tree'

    query_class = TreeQuery
    
    id = Column(Integer, nullable=False, autoincrement=True, primary_key=True)
    name = Column(String(64), nullable=False)
    version = Column(String(64), nullable=False)

    def __init__(self, name, version):
        self.name = name
        self.version = version
        
    
class Definitions(db.Model):
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
            db.session.add(rv)
            db.session.commit()
        return rv
    
        
class LangType(db.Model):
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
    
class Symbol(db.Model):
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
        qry = db.session.query(func.max(cls.symid).label('max_symid')).first()
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

    
class File(db.Model):
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
    
        
        
class Ref(db.Model):
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
    db.drop_all()        
    db.create_all()

