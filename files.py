import os
import string 

class Files(object):
    '''
    `pathname` startswith '/xxxx/xxx.py'
    '''
    
    def __init__(self, project_path):
        self.project_path = project_path
        
    def exists(self, pathname):
        return os.path.exists(self.toreal(pathname))
    
    def getdir(self, pathname):
        dirs, files = [], []
        realpath = self.toreal(pathname)
        for i in os.listdir(realpath):
            j = os.path.join(realpath, i)
            if os.path.isdir(j):
                dirs.append(i)
            elif os.path.isfile(j):
                files.append(i)
        return sorted(dirs), sorted(files)

    def getfp(self, pathname):
        return open(self.toreal(pathname))

    def get_lines(self, pathname):
        realpath = self.toreal(pathname)
        try:
            with open(realpath) as fp:
                return fp.readlines()
        except:
            with open(realpath, encoding='gbk') as fp:
                return fp.readlines()

    def get_txt(self, pathname):
        realpath = self.toreal(pathname)
        try:
            with open(realpath) as fp:
                return fp.read()
        except:
            with open(realpath, encoding='gbk') as fp:
                return fp.read()


    def isdir(self, pathname):
        real = self.toreal(pathname)
        return os.path.isdir(real)

    def isfile(self, pathname):
        real = self.toreal(pathname)
        return os.path.isfile(real)
        
    def gettime(self, pathname):
        mtime = os.path.getmtime(self.toreal(pathname))
        return mtime
    
    def getsize(self, pathname):
        return os.path.getsize(self.toreal(pathname))

    def gettype(self, pathname):
        idx = pathname.rfind(".")
        if idx > 0:
            ext = pathname[idx+1:].lower()
        else:
            ext = None
        if ext == 'py':
            return 'python'
        elif ext == 'c':
            return 'c'
        elif ext == 'cpp' or ext == 'cc' or ext == 'hpp':
            return 'c++'
        elif ext == 'h':
            return 'c++'
        elif ext == 'go':
            return 'go'

        if pathname == 'makefile':
            return 'makefile'
        elif pathname == 'readme':
            return 'readme'

        if self.istext(pathname):
            return 'text'
        return 'bin'

    def is_same_filetype(self, a, b):
        if a == b:
            return True
        if a in ('c', 'c++') and b in ('c', 'c++'):
            return True
        return False


    def parseable(self, pathname):
        ftype = self.gettype(pathname)
        if ftype in ['python', 'c++', 'c', 'h', 'go']:
            return True
        
        return False
    
    
    def istext(self, pathname):
        filename = self.toreal(pathname)
        try:
            s = open(filename).read(512)
        except:
            return False

        text_characters = "".join(list(map(chr, range(32, 127))) + list("\n\r\t\b"))
        import six
        # if six.PY3:
        #     _null_trans = str.maketrans("", "")
        # else:
        #     _null_trans = string.maketrans("", "")
        _null_trans = {ord(i):'' for i in text_characters}
        if not s:
            # Empty files are considered text
            return True
        if "\0" in s:
            # Files with null bytes are likely binary
            return False
        # Get the non-text characters (maps a character to itself then
        # use the 'remove' option to get rid of the text characters.)
        t = []
        for ch in s:
            if ord(ch) in _null_trans:
                continue
            t.append(ch)

        # t = s.translate(_null_trans)
        # t = s.translate(None, text_characters)
        # If more than 30% non-text characters, then
        # this is considered a binary file
        if float(len(t))/float(len(s)) > 0.30:
            return False
        return True
        
    
    def toreal(self, pathname):
        if pathname == '/':
            return self.project_path
        if pathname.startswith("/"):
            pathname = pathname[1:]
        return os.path.realpath(os.path.join(self.project_path, pathname))

    
    def filerev(self, pathname):
        return "-".join([str(self.getsize(pathname)),
                         str(self.gettime(pathname))])
    

if __name__ == "__main__":

    from conf import trees
    
    for project_path in trees.values():
        st = Files(project_path)
        pathname = '.'
        print(st.getdir(pathname))
