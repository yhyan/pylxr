#!/usr/bin/env python

import os
from subprocess import Popen, PIPE

current_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(current_dir, 'template')

data_dir = os.path.join(current_dir, 'data')
source_root = os.path.join(data_dir, 'source')
index_dir = os.path.join(data_dir, 'index')

cookie_secret = '__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__'


trees = {
    'redispy': os.path.join(source_root, 'redispy/2.10.3'),

}
