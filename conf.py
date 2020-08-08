#!/usr/bin/env python

import os
from subprocess import Popen, PIPE

current_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(current_dir, 'template')

try:
    from local_conf import data_dir, source_root, index_dir, trees
    from local_conf import cookie_secret
except ImportError as e:
    data_dir = os.path.join(current_dir, 'data')
    source_root = os.path.join(current_dir, 'data/source/')
    index_dir = os.path.join(current_dir, 'data/index/')

    # tornado cookie secret
    cookie_secret = '__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__'

    trees = {
        # for debug
        'redispy': {
            'name': 'redispy',
            'desc': 'redispy',
            'sourceroot': os.path.join(source_root, 'redispy'),
            'versions': ['2.10.3'],
            'version': '2.10.3',
        },
    }


config = {
    'swishbin': "/usr/bin/swish-e", # Popen(["which", "swish-e"], stdout=PIPE).communicate()[0].rstrip(),
    'swishconf': os.path.join(template_dir, 'swish-e.conf'),
    'swishdirbase': index_dir,

    'ectagsbin': '/usr/bin/ctags', # Popen(["which", "ctags"], stdout=PIPE).communicate()[0].rstrip(),
    'ectagsopts': ' '.join(['--options=%s' % os.path.join(template_dir, 'ectags.conf'),
                            '--c-types=+plx',
                            '--eiffel-types=+l',
                            '--fortran-types=+L']),

    'virtroot': '/lxr',

    'dbhost': '',
    'dbuser': '',
    'dbpass': '',
    'dbname': '',
}


