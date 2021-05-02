
class LangType(object):

    lang_py = 1000
    lang_c = 2000
    lang_go = 3000

    def_func = 1
    def_class = 2
    def_struct = 3
    def_define = 4
    def_variable = 5

    c_class = 2002
    c_define = 2004
    c_func = 2001
    c_struct = 2003
    c_variable = 2005

    go_class = 3002
    go_define = 3004
    go_func = 3001
    go_struct = 3003
    go_variable = 3005

    py_class = 1002
    py_define = 1004
    py_func = 1001
    py_struct = 1003
    py_variable = 1005

    @classmethod
    def format_lang_type(cls, i):

        lang_type = int(i / 1000) * 1000
        def_type = i % 1000

        lang = ''
        def_ = ''
        if def_type == 1:
            def_ = 'function'
        elif def_type == 2:
            def_ = 'class'
        elif def_type == 3:
            def_ = 'struct'
        elif def_type == 4:
            def_ = 'define'
        elif def_type == 5:
            def_ = 'variable'
        return lang, def_




