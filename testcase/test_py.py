#!/usr/bin/env python
#coding:utf-8

import ast
import os

curdir = os.path.dirname(os.path.realpath(__file__))

def main():
    from tags.python import find_tags

    tags = find_tags(os.path.join(curdir, '../pycparser/c_parser.py'))
    for tag in tags:
        print(tag)




if __name__ == "__main__":
    main()


