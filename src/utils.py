#!/usr/bin/env python
#coding:utf-8

import chardet

def smart_read(abspath, retrun_lines=False):
    txt = ''
    with open(abspath, 'rb') as fp:
        txt = fp.read()
    result = chardet.detect(txt)
    encoding = result['encoding']
    if encoding:
        # GB2312，GBK，GB18030，是兼容的，包含的字符个数：GB2312 < GBK < GB18030
        if encoding.lower() == 'gb2312':
            encoding = 'gb18030'
        try:
            txt = txt.decode(encoding)
        except:
            with open(abspath) as fp:
                txt = fp.read()
    if retrun_lines:
        return txt.splitlines(True)
    return txt

