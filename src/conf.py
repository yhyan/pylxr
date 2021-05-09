#!/usr/bin/env python

import os

current_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(current_dir, 'template')

try:
    from local_conf import data_dir, source_root, index_dir, trees
    from local_conf import cookie_secret
    from local_conf import is_debug_mode
except ImportError as e:
    import traceback
    print(traceback.format_exc())

    data_dir = os.path.join(current_dir, 'data')
    source_root = os.path.join(current_dir, 'data/source/')
    index_dir = os.path.join(current_dir, 'data/index/')
    is_debug_mode = False

    # tornado cookie secret
    cookie_secret = 'TODO:set your cookie secret'

    trees = {
        # for debug
        'redispy': os.path.join(source_root, 'redispy/2.10.3'),
    }


