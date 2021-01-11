一个web版的查看源代码的工具，从[lxr](https://en.wikipedia.org/wiki/LXR_Cross_Referencer)移植过来。

# Demo

[http://lxr.yanyahua.com/](http://lxr.yanyahua.com/)

# 使用方法

- 下载源代码

```
git clone git@github.com:yhyan/pylxr.git
cd pylxr
```

- 创建tag索引

创建一个local_conf.py，例如：

```
#!/usr/bin/env python

import os

current_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(current_dir, 'temp')

data_dir = '/data/lxr'

source_root = '/data/lxr/source/'

trees = {
    'redispy': {
        'name': 'redispy',
        'desc': 'redispy',
        'sourceroot': os.path.join(source_root, 'redispy'),
        'versions': ['2.10.3'],
        'version': '2.10.3',
        'display': True,
    },
}

```

创建tag索引

```
python genxref.py redispy
```

