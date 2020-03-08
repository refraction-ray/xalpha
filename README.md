xalpha
========

[![version](https://img.shields.io/pypi/v/xalpha.svg)](https://pypi.org/project/xalpha/)
[![doc](https://readthedocs.org/projects/xalpha/badge/?style=flat)](https://xalpha.readthedocs.io/) 	
[![Travis](https://api.travis-ci.org/refraction-ray/xalpha.svg)](https://travis-ci.org/refraction-ray/xalpha)
[![codecov](https://codecov.io/gh/refraction-ray/xalpha/branch/master/graph/badge.svg)](https://codecov.io/gh/refraction-ray/xalpha)
[![license](https://img.shields.io/:license-mit-blue.svg)](https://badges.mit-license.org/)

**国内基金投资的全流程管理**

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

一行获取历史日线数据或实时数据

```python
xa.get_daily("SH518880") # 沪深市场历史数据
xa.get_daily("USD/CNY") # 人民币中间价历史数据
xa.get_rt("commodities/crude-oil") # 原油期货实时数据
```

xalpha 不止如此，更多特性，欢迎探索。

## Documentation

文档地址： https://xalpha.readthedocs.io/ 

或者通过以下命令，在本地`doc/build/html`内阅读文档。

```bash
$ cd doc
$ make html
```


## Installation

```bash
pip install xalpha
```

目前仅支持 python 3 。

## Usage

由于丰富的可视化支持，建议配合 Jupyter Notebook 使用。可以参照[这里](https://xalpha.readthedocs.io/en/latest/demo.html)给出的示例连接，快速掌握大部分功能。
