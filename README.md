xalpha
========

[![version](https://img.shields.io/pypi/v/xalpha.svg)](https://pypi.org/project/xalpha/)
[![doc](https://readthedocs.org/projects/xalpha/badge/?style=flat)](https://xalpha.readthedocs.io/) 	
[![Travis](https://api.travis-ci.org/refraction-ray/xalpha.svg)](https://travis-ci.org/refraction-ray/xalpha)
[![codecov](https://codecov.io/gh/refraction-ray/xalpha/branch/master/graph/badge.svg)](https://codecov.io/gh/refraction-ray/xalpha)
[![license](https://img.shields.io/:license-mit-blue.svg)](https://badges.mit-license.org/)

**基金投资的全流程管理**

场外基金的信息与净值获取，精确到分的投资账户记录整合分析与丰富可视化，简单的策略回测以及根据预设策略的定时投资提醒。尤其适合资金反复进出的定投型和网格型投资的概览与管理分析。

🎉 最新版本支持通用日线和实时数据获取器，统一接口一行可以获得几乎任何市场上存在产品的价格数据，进行分析。

一行拿到基金信息：

```python
nfyy = xa.fundinfo("501018")
```

一行根据账单进行基金组合全模拟，和实盘完全相符:

```python
jiaoyidan = xa.record(path).status # 额外一行先读入 path 处的 csv 账单
shipan = xa.mul(jiaoyidan) # Let's rock
shipan.combsummary() # 看所有基金总结效果
```

一行获取各种金融产品的历史日线数据或实时数据

```python
xa.get_daily("SH518880") # 沪深市场历史数据
xa.get_daily("USD/CNY") # 人民币中间价历史数据
xa.get_rt("commodities/crude-oil") # 原油期货实时数据
xa.get_rt("HK00700", double_check=True) # 双重验证高稳定性支持的实时数据
```

一行拿到指数，行业，基金和个股的历史估值和即时估值分析（指数部分需要聚宽数据，本地试用申请或直接在聚宽云平台运行）

```python
xa.PEBHistory("SH000990").summary()
xa.PEBHistory("F100032").v()
```

xalpha 不止如此，更多特性，欢迎探索。不只是数据，更是工具！


## 文档

在线文档地址： https://xalpha.readthedocs.io/ 

或者通过以下命令，在本地`doc/build/html`内阅读文档。

```bash
$ cd doc
$ make html
```


## 安装

```bash
pip install xalpha
```

目前仅支持 python 3 。

若想要尝试最新版，

```bash
$ git clone https://github.com/refraction-ray/xalpha.git
$ cd xalpha && python3 setup.py install
```

## 用法

### 本地使用

由于丰富的可视化支持，建议配合 Jupyter Notebook 使用。可以参照[这里](https://xalpha.readthedocs.io/en/latest/demo.html)给出的示例连接，快速掌握大部分功能。

部分效果如下：

<img src="doc/source/kline.png" width="90%">

<img src="doc/source/tradecost.png" width="90%">

<img src="doc/source/positions.png" width="80%">



### 在量化平台使用

这里以聚宽为例，打开聚宽研究环境的 jupyter notebook，运行以下命令：

```
>>> !pip3 install xalpha --user
>>> import sys
>>> sys.path.insert(0, "/home/jquser/.local/lib/python3.6/site-packages")
>>> import xalpha as xa
```

即可在量化云平台正常使用 xalpha，并和云平台提供数据无缝结合。

如果想在云平台研究环境尝试最新开发版 xalpha，所需配置如下。

```
>>> !git clone https://github.com/refraction-ray/xalpha.git
>>> !cd xalpha && python3 setup.py develop --user
>>> import sys
>>> sys.path.insert(0, "/home/jquser/.local/lib/python3.6/site-packages")
>>> import xalpha as xa
```

由于 xalpha 整合了部分聚宽数据源的 API，在云端直接 ``xa.provider.set_jq_data(debug=True)`` 即可激活聚宽数据源。

## 致谢

感谢[集思录](https://www.jisilu.cn)对本项目的支持和赞助，可以在[这里](https://www.jisilu.cn/data/qdii/#qdiie)查看基于 xalpha 引擎构建的 QDII 基金净值预测。

## 博客

* [xalpha 诞生记](https://re-ra.xyz/xalpha-%E8%AF%9E%E7%94%9F%E8%AE%B0/)

* [xalpha 设计哲学及其他](https://re-ra.xyz/xalpha-%E8%AE%BE%E8%AE%A1%E5%93%B2%E5%AD%A6%E5%8F%8A%E5%85%B6%E4%BB%96/)