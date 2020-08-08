#!/usr/bin/env python

import re
import MySQLdb

class Index(object):
    
    def __init__(self, config, tree, initdb=False):
        self.db  = MySQLdb.connect(host=config['dbhost'],
                                   user=config['dbuser'],         
                                   passwd=config['dbpass'],
                                   db=config['dbname'])
        self.db.autocommit(True)
        self.cur = self.db.cursor()   
        self.table_prifix = tree['name']

        if initdb:
            self.init_table()
        
        self.filenum = 0
        
        self.files = {}
        self.symcache = {}
        self.cntcache = {}
        self.total_sym = 0

        self.allfiles_select = "select f.fileid, f.filename, f.revision, t.relcount" \
                               " from lxr_files f, lxr_status t"\
                               ", lxr_releases r"\
                               ' where r.releaseid = ?'\
                               '  and  f.fileid = r.fileid'\
                               '  and  t.fileid = r.fileid'\
                               ' order by f.filename, f.revision'\



        self.symbols_byid = "select symname from lxr_symbols"\
                            ' where symid = ?'

        self.symbols_setref = ("update lxr_symbols"
                               + ' set symcount = ?'
                               + ' where symid = ?'
                               )

        self.related_symbols_select = ('select s.symid, s.symcount, s.symname'
                                       + " from lxr_symbols s, lxr_definitions d"
                                       + ' where d.fileid = ?'
                                       + '  and  s.symid = d.relid')

        self.delete_symbols = ("delete from lxr_symbols"
                               + ' where symcount = 0'
                               )



        self.delete_file_definitions = ("delete from lxr_definitions"
                                        + ' where fileid  = ?'
                                        )

        self.delete_definitions = ("delete from lxr_definitions"
                                   + ' where fileid in'
                                   + ' (select r.fileid'
                                   + "  from lxr_releases r, lxr_status t"
                                   + '  where r.releaseid = ?'
                                   + '   and  t.fileid = r.fileid'
                                   + '   and  t.relcount = 1'
                                   + ' )'
                                   )

        self.releases_insert = ("insert into lxr_releases"
                                + ' (fileid, releaseid)'
                                + ' values (?, ?)'
                                )

        self.releases_select = ("select fileid from lxr_releases"
                                + ' where fileid = ?'
                                + ' and  releaseid = ?'
                                )

        self.delete_one_release = ("delete from lxr_releases"
                                   + ' where fileid = ?'
                                   + '  and  releaseid = ?'
                                   )
        self.delete_releases = ("delete from lxr_releases"
                                + ' where releaseid = ?'
                                )


        self.status_timestamp = ("select indextime from lxr_status"
                                 + ' where fileid = ?'
                                 )

        self.status_update_timestamp = ("update lxr_status"
                                        + ' set indextime = ?'
                                        + ' where fileid = ?'
                                        )

        self.delete_unused_status = ("delete from lxr_status"
                                     + ' where relcount = 0'
                                     )

        self.usages_insert = ("insert into lxr_usages"
                              + ' (fileid, line, symid)'
                              + ' values (?, ?, ?)'
                              )

        self.usages_select = ('select f.filename, u.line'
                              + " from lxr_symbols s, lxr_files f"
                              + ", lxr_releases r, lxr_usages u"
                              + ' where s.symname = ?'
                              + '  and  r.releaseid = ?'
                              + '  and  u.symid  = s.symid'
                              + '  and  f.fileid = r.fileid'
                              + '  and  u.fileid = r.fileid'
                              + ' order by f.filename, u.line'
                              )

        self.delete_file_usages = ("delete from lxr_usages"
                                   + ' where fileid  = ?'
                                   )

        self.delete_usages = ("delete from lxr_usages"
                              + ' where fileid in'
                              + ' (select r.fileid'
                              + "  from lxr_releases r, lxr_status t"
                              + '  where r.releaseid = ?'
                              + '   and  t.fileid = r.fileid'
                              + '   and  t.relcount = 1'
                              + ' )'
                              )


        self.purge_all = ("truncate table lxr_definitions"
                          + ", lxr_usages, lxr_langtypes"
                          + ", lxr_symbols, lxr_releases"
                          + ", lxr_status, lxr_files"
                          + ' cascade'
                          )


    def __delete__(self):
        self.db.commit()
        self.db.close()

    def init_table(self):
        sqls = [
            'drop table if exists lxr_filenum;',
            'drop table if exists lxr_symnum;',
            'drop table if exists lxr_typenum;',
        
            'create table lxr_filenum ( rcd int primary key, fid int);',
            'insert into lxr_filenum (rcd, fid) VALUES (0, 0);',
        
            'create table lxr_symnum ( rcd int primary key , sid int);',
            'insert into lxr_symnum (rcd, sid) VALUES (0, 0);',
        
            'create table lxr_typenum ( rcd int primary key, tid int);',
            'insert into lxr_typenum (rcd, tid) VALUES (0, 0);',
        
            'alter table lxr_filenum engine = MyISAM;',
            'alter table lxr_symnum engine = MyISAM;',
            'alter table lxr_typenum engine = MyISAM;',

            'drop table if exists lxr_files;',
            
            '''
            create table lxr_files
	    ( fileid    int                not null primary key
	    , filename  varbinary(255)     not null
	    , revision  varbinary(255)     not null
	    , constraint lxr_uk_files unique (filename, revision)
	    , index lxr_filelookup (filename)
	    )
	    engine = MyISAM;''',

            'drop table if exists lxr_status;',
            
            '''
            create table lxr_status
	    ( fileid    int     not null primary key
	    , relcount  int
	    , indextime int
	    , status    tinyint not null
	    , constraint lxr_fk_sts_file foreign key (fileid) references lxr_files(fileid)
	    )
	    engine = MyISAM;''',

            'drop trigger if exists lxr_remove_file;',
            
            'create trigger lxr_remove_file after delete on lxr_status for each row delete from lxr_files where fileid = old.fileid;',

            'drop table if exists lxr_releases;',
            
            '''create table lxr_releases
	    ( fileid    int            not null
	    , releaseid varbinary(255) not null
	    , constraint lxr_pk_releases primary key (fileid, releaseid)
	    , constraint lxr_fk_rls_fileid foreign key (fileid) references lxr_files(fileid)
	    )
	    engine = MyISAM;''',

            'drop trigger if exists lxr_add_release;',
            
            '''create trigger lxr_add_release 
            after insert on lxr_releases for each row update lxr_status set relcount = relcount + 1 where fileid = new.fileid;''',
            
            'drop trigger if exists lxr_remove_release;',
            
            '''create trigger lxr_remove_release after delete on lxr_releases for each row update lxr_status set relcount=relcount-1, status=0
            where fileid = old.fileid and relcount > 0;''',

            'drop table if exists lxr_langtypes;',
            
            '''create table lxr_langtypes
	    ( typeid       smallint         not null
	    , langid       tinyint unsigned not null
	    , declaration  varchar(255)     not null
	    , constraint lxr_pk_langtypes
	    primary key  (typeid, langid)
	    )
	    engine = MyISAM;''',

            'drop table if exists lxr_symbols;',
            
            '''create table lxr_symbols
	    ( symid    int            not null                primary key
	    , symcount int
	    , symname  varbinary(255) not null unique
	    )
	    engine = MyISAM;''',

            'drop procedure if exists lxr_decsym',
            
            '''delimiter //
            create procedure lxr_decsym(in whichsym int)
            begin
	    update lxr_symbols
	    set	symcount = symcount - 1
	    where symid = whichsym
	    and symcount > 0;
            end//
            delimiter ;''',

            'drop table if exists lxr_definitions;',
            
            '''create table lxr_definitions
	    ( symid   int              not null
	    , fileid  int              not null
	    , line    int              not null
	    , typeid  smallint         not null
	    , langid  tinyint unsigned not null
	    , relid   int
	    , index lxr_i_definitions (symid)
	    , constraint lxr_fk_defn_symid
	    foreign key (symid)
	    references lxr_symbols(symid)
	    , constraint lxr_fk_defn_fileid
	    foreign key (fileid)
	    references lxr_files(fileid)
	    , constraint lxr_fk_defn_type
	    foreign key (typeid, langid)
	    references lxr_langtypes(typeid, langid)
	    , constraint lxr_fk_defn_relid
	    foreign key (relid)
	    references lxr_symbols(symid)
	    )
	    engine = MyISAM;''',

            'drop trigger if exists lxr_remove_definition;',
            
            '''delimiter //
            create trigger lxr_remove_definition
	    after delete on lxr_definitions
	    for each row
	    begin
	    call lxr_decsym(old.symid);
	    if old.relid is not null
	    then call lxr_decsym(old.relid);
	    end if;
	    end//
            delimiter ;''',

            'drop table if exists lxr_usages;',
            
            '''create table lxr_usages
	    ( symid   int not null
	    , fileid  int not null
	    , line    int not null
	    , index lxr_i_usages (symid)
	    , constraint lxr_fk_use_symid
	    foreign key (symid)
	    references lxr_symbols(symid)
	    , constraint lxr_fk_use_fileid
	    foreign key (fileid)
	    references lxr_files(fileid)
	    )
	    engine = MyISAM;''',

            'drop trigger if exists lxr_remove_usage;',
            
            '''
            create trigger lxr_remove_usage
	    after delete on lxr_usages
	    for each row
	    call lxr_decsym(old.symid);''',

            'drop procedure if exists lxr_PurgeAll',
            
            '''delimiter //
            create procedure lxr_PurgeAll ()
            begin
	    set @old_check = @@session.foreign_key_checks;
	    set session foreign_key_checks = OFF;
	    truncate table lxr_filenum;
	    truncate table lxr_symnum;
	    truncate table lxr_typenum;
	    insert into lxr_filenum
	    (rcd, fid) VALUES (0, 0);
	    insert into lxr_symnum
	    (rcd, sid) VALUES (0, 0);
	    insert into lxr_typenum
	    (rcd, tid) VALUES (0, 0);
	    truncate table lxr_definitions;
	    truncate table lxr_usages;
	    truncate table lxr_langtypes;
	    truncate table lxr_symbols;
	    truncate table lxr_releases;
	    truncate table lxr_status;
	    truncate table lxr_files;
	    set session foreign_key_checks = @old_check;
            end//
            delimiter ;'''
            
        ]

        for sql in sqls:
            sql = sql.replace('lxr', self.table_prifix)

            try:
                if sql.find('delimiter') >= 0:
                    delimiters = re.compile('DELIMITER *(\S*)',re.I)
                    result = delimiters.split(sql)

                    # Insert default delimiter and separate delimiters and sql
                    result.insert(0,';') 
                    delimiter = result[0::2]
                    section   = result[1::2]

                    # Split queries on delimiters and execute
                    for i in range(len(delimiter)):
                        queries = section[i].split(delimiter[i])
                        for query in queries:
                            if not query.strip():
                                continue
                            self.cur.execute(query)
                else:
                    self.cur.execute(sql)
            except Exception as e:
                print(e)
                print(sql)
            self.db.commit()
        return

    

    def status_select(self, fileid):
        sql = '''select status from %s_status where fileid = %s''' % (self.table_prifix, fileid)
        self.cur.execute(sql)
        ss = [row[0] for row in self.cur.fetchall()]
        if ss:
            return ss[0]
        return None

    def status_update(self, fileid, status):
        sql = "update %s_status set status = %s where fileid = %s" % (self.table_prifix, status, fileid)
        return self.cur.execute(sql)

    def status_insert(self, fileid, status):
        sql = '''insert into %s_status 
        (fileid, relcount, indextime, status)
        values (%s, 0, 0, %s)''' % (self.table_prifix, fileid, status)
        
        return self.cur.execute(sql)
        

    def files_insert(self, filename, revision, fileid):
        sql = "insert into %s_files (filename, revision, fileid) values ('%s', '%s', %s)" % (
            self.table_prifix, filename, revision, fileid)
        return self.cur.execute(sql)
        
 
    def fileidifexists(self, pathname, revision):
        sql = "select fileid from %s_files where filename = '%s' and revision = '%s'" % (
            self.table_prifix, pathname, revision)
        self.cur.execute(sql)
        ids = [row[0] for row in self.cur.fetchall()]
        if ids:
            return ids[0]
        return None

    
    def fileid(self, pathname, revision):
        _id = self.fileidifexists(pathname, revision)
        if _id is None:
            self.filenum += 1
            _id = self.filenum
            self.files_insert(pathname, revision, _id)
            self.status_insert(_id, 0)
        return _id
    

    def fileindexed(self, fileid):
        status = self.status_select(fileid)
        if status is not None and status & 1:
            return True
        return False
    
    def setfileindexed(self, fileid):
        status = self.status_select(fileid)
        if status is None:
            self.status_insert(fileid, 1)
        elif status & 1 == 0:
            self.status_update(fileid, status ^ 1)
            
    def filereferenced(self, fileid):
        status = self.status_select(fileid)
        if status is not None and status & 1:
            return True
        return False

    def setfilereferenced(self, fileid):
        status = self.status_select(fileid)
        if status is None:
            self.status_insert(fileid, 2)
        elif status & 1 == 0:
            self.status_update(fileid, status ^ 2)

    def symbols_byname(self, symname):
        sql = '''select symid, symcount from %s_symbols where symname = "%s"''' % (self.table_prifix, symname)
        self.cur.execute(sql)
        ss = [(row[0], row[1]) for row in self.cur.fetchall()]
        if ss:
            return ss[0]
        
        return None, 0

    def symbols_insert(self, symname, symid):
        sql = "insert into %s_symbols (symname, symid, symcount) values ('%s', %s, 0)" % (self.table_prifix, symname, symid)
        self.cur.execute(sql)
        
    def symdeclarations(self, ident, releaseid):
        sql = '''select f.filename, d.line, l.declaration, d.relid
        from 
        %s_symbols s, %s_definitions d, %s_files f, %s_releases r, %s_langtypes l
        where s.symname = '%s' and  r.releaseid = '%s' and  d.fileid = r.fileid and  d.symid  = s.symid  and  d.langid = l.langid 
        and  d.typeid = l.typeid and  f.fileid = r.fileid
        order by f.filename, d.line, l.declaration''' % (self.table_prifix, self.table_prifix, self.table_prifix,
                                                         self.table_prifix, self.table_prifix,
                                                         ident, releaseid)
        self.cur.execute(sql)
        print(sql)
        ss = [(row[0], row[1], row[2], row[3]) for row in self.cur.fetchall()]
        return ss
            

    
    def symid(self, symname):
        if not symname:
            return None
        
        symid, symcount = self.symbols_byname(symname)
        if symid is None:
            sid = self.total_sym
            self.total_sym += 1
            self.symbols_insert(symname, sid)
            return sid
        return symid
    
    def setsymdeclaration(self, symname, fileid, line_no, langid, typeid, relsym):
        sid = self.symid(symname)
        relid = self.symid(relsym)
        sql = '''insert into %s_definitions (`symid`, `fileid`,`line`,`langid`,`typeid`,`relid`)  values (%%s, %%s, %%s, %%s, %%s, %%s)''' % (self.table_prifix)

        args = (sid, fileid, line_no, langid, typeid, relid)
        return self.cur.execute(sql, args)
        
    def issymbol(self, symname, releaseid):
        symid, symcount = self.symbols_byname(symname)
        if symid:
            return True
        return False
    

    def langtypes_insert(self, typeid, langid, declaration):
        sql = """insert into %s_langtypes(typeid, langid, declaration) 
        values (%s, %s, '%s')""" % (self.table_prifix, typeid, langid, declaration)
        print(sql)
        return self.cur.execute(sql)
    
        
    def langtypes_select(self, langid, declaration):
        sql = '''select typeid from %s_langtypes 
        where langid = %s and declaration = "%s"''' % (self.table_prifix, langid, declaration)
        self.cur.execute(sql)
        ss = [row[0] for row in self.cur.fetchall()]
        if ss:
            return ss[0]
        return -1

    def langtypes_count(self):
        sql = "select max(typeid) + 1 from %s_langtypes" % (self.table_prifix)
        self.cur.execute(sql)
        ss = [row[0] for row in self.cur.fetchall()]
        if not ss[0]:
            self.total_sym += 1
            return self.total_sym
        return ss[0]


    def flushcache(self):
        pass
    

if __name__ == "__main__":
    from conf import trees
    from conf import config

    tree = trees['sqlalchemy']
    index = Index(config, tree, True)
