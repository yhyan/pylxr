#!/usr/bin/env python

import subprocess

from conf import config

def ctags(abspath, lang):
    # print(abspath)
    if lang not in ('python', 'c', 'c++', 'go'):
        return []

    #if lang in ('python', 'go',):
    return ctags_v2(abspath, lang)



    cmd = str('%s %s --excmd=number --language-force=%s -f - %s' % (str(config['ectagsbin']), config['ectagsopts'], lang, abspath))

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    if not out:
        return []
    tags = []

    out = out.decode('utf-8')
    lines = out.split("\n")
    for li in lines:
        if not li:
            continue
        values = li.rstrip().split("\t")
        if len(values) == 5:
            c_sym, c_file, c_line, c_type, c_ext = values
        elif len(values) == 4:
            c_sym, c_file, c_line, c_type = values
            c_ext = None
        elif len(values) >= 6:
            c_sym, c_file, c_line, c_type, c_ext = values[0:5]
        else:
            print('li=%s' % li)
            continue
        c_line = int(c_line.replace(';"', ''))
        tags.append([c_sym, c_line, c_type, c_ext])
    return tags



def ctags_v2(abspath, lang):
    from tags.base import find_tags
    return find_tags(abspath, lang)
