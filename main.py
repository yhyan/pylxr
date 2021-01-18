#!/usr/bin/env python
import logging
import tornado.escape
import tornado.ioloop
import tornado.web
import os.path
import uuid

from tornado import httpserver
from tornado.concurrent import Future
from tornado import gen
from tornado.options import define, options, parse_command_line
from tornado import template

from files import Files

import conf

from models import Symbol, Ref, Definitions, SwitchEngine, get_engine
from dbcache import langcache, filecache, symbolcache

# localhost:8888  chrome 测试时，port=8888会访问不了静态文件。

define("port", default=9999, help="run on the given port", type=int)


class MainHandler(tornado.web.RequestHandler):

    def on_finish(self):
        # db.session.remove()
        pass

    def prepare(self):
        self.page = None
        self.page_text = ''
        self.reqfile = None
        self.tree = None
        self.files = None
        self.project_version = ''
        self.detail = {}
        self.detail['trees'] = self.get_all_trees()
        self.detail['pages'] = {
            'source': 'Source navigation',
            'ident': 'Identifier search',
            'search': 'General search'
        }




    def get_all_trees(self):
        items = conf.trees.values()
        ret = []
        for tree in items:
            dbfile = '%s.%s.sqlite3' % (tree['name'], tree['version'])
            from conf import index_dir
            dbfile = os.path.join(index_dir, dbfile)
            if os.path.exists(dbfile):
                ret.append(tree)
        return ret





    def _identfile(self, filename):
        return '''<a class="identfile" href="/source/%s%s">%s</a>''' % (
            self.tree['name'], filename, filename)

    def _identline(self, filename, line):
        return '''<a class="identline" href="/source/%s%s#%04d">%d</a>''' % (
            self.tree['name'], filename, line, line)

    def return_ident_page(self):


        ident = self.get_argument('_i', '')

        symid = symbolcache.get_symid(self.project_name, self.project_version, ident)
        if not symid:
            defs = []
            refs = {}
        else:
            with SwitchEngine(get_engine(self.project_name, self.project_version)):
                objs = Definitions.query.filter(Definitions.symid==symid).all()
            defs = []
            for o in objs:
                lang, desc = langcache.get_lang_desc(self.project_name,
                                                     self.project_version,
                                                     o.typeid)


                filename = filecache.get_filename(self.project_name,
                                                         self.project_version,
                                                         o.fileid)

                defs.append(
                    (desc,
                     self._identfile(filename),
                     self._identline(filename, o.line)
                    )
                )

            with SwitchEngine(get_engine(self.project_name, self.project_version)):
                objs = Ref.query.filter(Ref.symid==symid).all()
            refs = {}
            for o in objs:

                filename = filecache.get_filename(self.project_name, self.project_version, o.fileid)
                item = (self._identfile(filename), self._identline(filename, o.line))
                if o.fileid in refs:
                    refs[o.fileid].append(item)
                else:
                    refs[o.fileid] = [item]

        self.detail['defs'] = defs
        self.detail['refs'] = refs.values()
        self.detail['ident'] = ident
        self.render("ident.html", **self.detail)

    def _calc_dir_content(self):
        dirs, files = self.files.getdir(self.reqfile, self.project_version)
        if not dirs and not files:
            return '''<p class="error">\n<i>The directory /%s does not exist, is empty or is hidden by an exclusion rule.</i>\n</p>\n''' % self.reqfile

        res = []
        _count = 0
        if self.reqfile != '/':
            i = {}
            i['name'] = "Parent directory"
            i['class'] = 'dirfolder'
            i['dirclass'] = 'dirrow%d' % (_count%2 + 1)
            i['href'] = "/source/%s%s" % (self.tree['name'], os.path.dirname(self.reqfile))
            i['img'] = '/icons/back.gif'
            i['filesize'] = '-'
            i['modtime'] = '-'
            i['desc'] = ''
            _count += 1
            res.append(i)


        for dir_name in dirs:
            i = {}
            i['name'] = dir_name + "/"
            i['class'] = 'dirfolder'
            i['dirclass'] = 'dirrow%d' % (_count%2 + 1)
            if self.reqfile and self.reqfile != '/':
                i['href'] = "/source/%s%s/%s" % (self.tree['name'], self.reqfile, dir_name)
            else:
                i['href'] = "/source/%s/%s" % (self.tree['name'], dir_name)
            i['img'] = '/icons/folder.gif'
            i['filesize'] = '-'
            i['modtime'] = '-'
            i['desc'] = ''
            _count += 1
            res.append(i)
        for file_name in files:
            i = {}
            i['name'] = file_name
            i['class'] = 'dirfile'
            i['dirclass'] = 'dirrow%d' % (_count%2 + 1)
            if self.reqfile != '/':
                i['href'] = "/source/%s%s/%s" % (self.tree['name'], self.reqfile, file_name)
            else:
                i['href'] = "/source/%s/%s" % (self.tree['name'], file_name)
            i['img'] = '/icons/generic.gif'
            i['filesize'] = '-'
            i['modtime'] = '-'
            i['desc'] = ''
            _count += 1
            res.append(i)
        loader = template.Loader(self.settings['template_path'])
        html = loader.load('htmldir.html').generate(files=res, desc='')
        return html

    def _calc_code_file(self):
        from simpleparse import PythonParse, CParse, CPPParse, GOParse

        if self.reqfile.lower().endswith(".py"):
            parse = PythonParse(conf.config, self.tree)
        elif self.reqfile.lower().endswith(".c"):
            parse = CParse(conf.config, self.tree)
        elif self.reqfile.lower().endswith(".cpp"):
            parse = CPPParse(conf.config, self.tree)
        elif self.reqfile.lower().endswith(".h"):
            parse = CPPParse(conf.config, self.tree)
        elif self.reqfile.lower().endswith('.go'):
            parse = GOParse(conf.config, self.tree)
        else:
            parse = None
        if parse:
            parse.parse_file(self.reqfile, self.project_version)
            return parse.out()
        return self._calc_raw_file()

    def _calc_raw_file(self):
        html = '''<pre class="filecontent">'''
        fp = self.files.getfp(self.reqfile, self.project_version)
        lineno = 0
        for li in fp:
            lineno += 1
            html += '''<a class='fline' name="%04d">%04d</a> %s''' % (lineno, lineno, li)
        fp.close()
        html += '''</pre>'''
        return html

    def _calc_text_file(self):
        html = '''<pre class="filecontent">'''
        fp = self.files.getfp(self.reqfile, self.project_version)
        html += fp.read()
        fp.close()
        html += '''</pre>'''
        return html

    def _calc_html_file(self):
        fp = self.files.getfp(self.reqfile, self.project_version)
        html = fp.read()
        fp.close()
        return html

    def _calc_source_content(self):
        if self.get_argument('raw', None) == '1':
            return self._calc_text_file()
        if self.files.isdir(self.reqfile, self.project_version):
            return self._calc_dir_content()
        elif self.files.parseable(self.reqfile, self.project_version):
            return self._calc_code_file()
        elif self.reqfile.lower().endswith('html'):
            return self._calc_html_file()
        else:
            return self._calc_raw_file()

    def return_source_page(self):
        self.detail['source_content'] = self._calc_source_content()
        self.render("source.html", **self.detail)

    def return_search_page(self):
        # TODO general search page
        self.detail['filetext'] = self.get_argument('filetext', '')
        self.detail['searchtext'] = self.get_argument('searchtext', '')
        self.detail['results'] = []
        self.detail['advancedchecked'] = self.get_argument('advancedchecked', '')
        self.detail['casesensitivechecked'] = self.get_argument('casesensitivechecked', '')
        self.render("search.html", **self.detail)


    def return_index_page(self):
        self.render("index.html", **self.detail)


    def get_banner_reqfile(self):
        htmls = []
        href = '/source/%s' % self.tree['name']
        paths = filter(None, self.reqfile.split('/'))
        htmls.append('<span class="banner">')
        htmls.append('<a class="banner" href="%s">%s</a>' % (href, self.tree['version']))
        for path in paths:
            href = href + '/' + path
            htmls.append('/')
            htmls.append('<a class="banner" href="%s">%s</a>' % (href, path))
        htmls.append('</span>')
        return ''.join(htmls)


    def get(self, *args):
        '''
        args[0] 'search', 'ident', 'source'
        args[1] treename
        '''

        if len(args) <= 1:
            self.page = 'index'
            return self.return_index_page()
        else:
            self.page = args[0]

        if self.page == 'index':
            self.return_index_page()
            return


        self.tree = conf.trees.get(args[1])
        self.project_name = self.tree['name']
        self.project_version = self.tree['version']

        self.files = Files(conf.trees.get(args[1]))

        if len(args) >= 3:
            self.reqfile = args[2] or '/'
        else:
            self.reqfile = '/'
        self.detail['tree'] = self.tree
        self.detail['reqfile'] = self.reqfile
        self.detail['banner_reqfile'] = self.get_banner_reqfile()
        self.detail['files'] = self.files
        self.detail['page'] = self.page
        if self.page == 'search':
            self.return_search_page()
        elif self.page == 'ident':
            self.return_ident_page()
        elif self.page == 'source':
            self.return_source_page()
        else:
            self.return_index_page()



def main():
    tornado.options.parse_command_line()
    from conf import is_debug_mode
    settings = dict(
        cookie_secret=conf.cookie_secret,
        template_path=os.path.join(os.path.dirname(__file__), "template/html"),
        static_path=os.path.join(os.path.dirname(__file__), "template"),
        xsrf_cookies=True,
        debug=is_debug_mode,
    )

    mapping = [
        (r"/static/(.+)", tornado.web.StaticFileHandler, dict(path=settings['static_path'])),
        (r"/icons/(.+)", tornado.web.StaticFileHandler, dict(path=settings['static_path']+"/icons/")),
        (r"/(\w+)/(\w+)(/.*)?", MainHandler),
        (r"/", MainHandler),
    ]
    app = tornado.web.Application(
        mapping, **settings
    )

    http_server = httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
