#!/usr/bin/env python


def ctags(abspath, lang):
    # print(abspath)
    if lang not in ('python', 'c', 'c++', 'go'):
        return []

    from tags.base import find_tags
    return find_tags(abspath, lang)
