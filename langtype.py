
class LangType(object):

    lang_py = 1000
    lang_c = 2000
    lang_go = 3000

    def_func = 1
    def_class = 2
    def_struct = 3
    def_define = 4
    def_variable = 5

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




