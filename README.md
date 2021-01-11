一个web版的查看源代码的工具，从[lxr](https://en.wikipedia.org/wiki/LXR_Cross_Referencer)移植过来。

核心功能：根据标识符(identifier)查询索引，只支持python，c，c++，go语言。

python源码支持的identifier：

- AsyncFunctionDef
- FunctionDef
- ClassDef

C语言支持的identifier：

C++支持的identifier：

Go支持的identifier：





# Demo

[http://lxr.yanyahua.com/](http://lxr.yanyahua.com/)

# 使用方法

- 下载源代码

```
git clone git@github.com:yhyan/pylxr.git
cd pylxr
```

- 创建local_conf.py，例如：

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

- 创建tag索引

```
python genxref.py redispy
```

- 启动程序

```
python main.py
```

# 实现原理

解析每个源码文件里面的identifier，然后扫描每个源码文件中是否存在该identifier，将所有的索引关系储存到sqlite中。

核心点在于编写每种编程语言的parser。


