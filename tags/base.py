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
    if lang == 'go':
        import tags.go as mod
    elif lang == 'c':
        import tags.c as mod
    elif lang == 'cpp':
        import tags.cpp as mod
    elif lang == 'python':
        import tags.python as mod
    else:
        print('unknown lang=%s' % lang)
        return []

    return mod.find_tags(abspath)

