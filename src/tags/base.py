#!/usr/bin/env python
#coding:utf-8

class SourceFile(object):

    def __init__(self, path):
        self.path = path


    def getc(self):
        pass

    def ungetc(self, c):
        pass

    def getline(self):
        pass


def find_tags(abspath, lang):
    if lang not in ('python', 'c', 'c++', 'go', 'asm'):
        return []

    if lang == 'go':
        import tags.go as mod
    elif lang in ( 'c', 'c++', 'cpp'):
        import tags.c as mod
    elif lang == 'python':
        import tags.python as mod
    elif lang == 'asm':
        import tags.asm as mod
    else:
        print('unknown lang=%s' % lang)
        return []

    return mod.find_tags(abspath)


