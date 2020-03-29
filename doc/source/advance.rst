.. _advance:

===========
高级用法
===========

数据缓存
--------

xalpha 有两部分可以提供数据缓存和本地化。

基金交易部分数据
+++++++++++++++++++

第一部分是本地化与增量更新 info 系列的对象，比如 ``fundinfo``, ``indexinfo``, ``mfundinfo`` 等，这样就不需要每次再去爬取处理以前的净值，费率等等。
其本地化的不只是净值数据，也包括基金名称，基金费率等元信息。

其使用方法是，直接将 ``fetch=True`` （首先尝试从本地读取数据）,
``save=True`` （更新的数据存回本地）, ``form="csv"/"sql"`` （本地后端是 csv 文件还是 sql 数据库） 和
``path="path"/engine`` （对应 csv 的本地存储路径或对应 sql 的 SQLAlchemy.engine 类.
作为参数传入 ``fundinfo`` 等。
如果是基金组合，也可以直接将这些参数传入 `mul` 或 `mulfix` 类。
格式为 sql 时， path 示例：

.. code-block:: python

    import xalpha as xa
    from sqlalchemy import create_engine
    engine = create_engine('mysql://root:password@127.0.0.1/database?charset=utf8')
    io = {"save": True, "fetch": True, "format": "sql", "path": engine}
    xa.fundinfo("510018", **io)


get_daily 数据透明缓存
++++++++++++++++++++++++++++

第二部分本地化和缓存是专门针对 ``get_daily`` 界面的，用于存储对应的日期-价格表。这一部分的缓存和本地化更加透明。不需要任何设置，``get_daily`` 就自带内存缓存，
不会去爬取重复数据。如果想要把数据本地化存储，只需要 ``xa.set_backend(backend=, path=, prefix=, precached=)`` 即可。

其中 backend 同样可以是 csv 和 sql，也可以是默认的 memory。
path 与第一部分相同为 csv 存储的文件夹或 sql 的 engine 对象。prefix 是每个表单会添加的前缀，否则默认是用 code 做键值。
precached 可以不设，若设置为 %Y%m%d 的时间字符串格式，则代表第一次爬取就"预热"从 precached 到昨日的数据缓存。
注意到即使选取了数据库或文件作为后端，内存作为二级缓存依旧发挥作用，只要数据不改变，仍会直接读取内存数据，因此提升读写数据速度。

如果担忧内存中数据被"污染"，可以通过 ``xa.universal.check_cache(code, start, end)`` 来校验对应数据的准确性。也可用 ``xa.universal.reset_cache()`` 来清空现有的内存数据缓存。


最后为了可以在运行时动态改变 xalpha 函数的缓存行为，也即任何时刻 ``xa.set_backend`` 都可以生效，xalpha 强烈推荐所有函数，都以 ``xa.meth`` 的形式使用，
强烈不建议 ``from xalpha import meth`` 这种导入方式。


数据本地化
-------------
数据缓存部分提供的方法已经足够满足绝大多数数据本地化的要求，可以透明地将数据落地到本地文件系统或关系型数据库。

如果需要更复杂的本地化需求，考虑到 xalpha 中所有数据都是以 pandas.DataFrame 格式存在，那么只需参考 DataFrame 的 IO 功能即可 `IOTools <https://pandas.pydata.org/pandas-docs/stable/user_guide/io.html>`_ 。
数据可以一键落地到 csv， excel， hdf5， json，html， 数据库表格等格式。


数据可视化
----------------

xalpha 提供两部分的可视化。对于基金管理部分，相关类所有以 ``v_`` 开始的方法，均是 pyecharts 支持的可视化封装。
对于 toolbox 部分，``v()`` 方法，是 matplotlib 支持的可视化。

此外，考虑到所有数据均是 DataFrame 格式，用户也可以对任何数据，轻松可视化，参考代码 ``df.plot(x="date", y=["open", "close"])``.
更多关于对 DataFrame 的可视化，请参考 Pandas 文档， `Visualization <https://pandas.pydata.org/pandas-docs/stable/user_guide/visualization.html>`_ 。


数据提供商
------------

xalpha 的数据来自天天基金，英为财情，雪球，彭博，标普，新浪财经，网易财经，雅虎财经等多个源头，xalpha 的哲学是尽量利用免费的透明数据源。
但有些数据还是会依赖需要鉴权的数据 API，这些被抽象成数据提供商。

比如 xalpha 的历史估值系统，依赖聚宽的数据，那么就有两种方案。

本地调用聚宽数据
+++++++++++++++++++

第一种是本地 ``pip install jqdatasdk`` 并且申请聚宽的本地数据试用权限（免费），
之后通过 ``xa.provider.set_jq_data(user, password)`` 即可。

如果希望不需要每次使用 xalpha 都重新鉴权，也可以在 ``set_jq_data`` 添加 ``persistent=True``
的选项，这样聚宽账户密码会简单编码后存在本地（无加密保护，请自行衡量安全性），以后每次 ``import xalpha`` 聚宽的数据源都会自动激活。

云端使用 xalpha
+++++++++++++++++

第二种方案不需要聚宽本地数据，而是直接在聚宽云平台的研究环境来使用 xalpha，此时的初始化配置为::

    >>> !pip3 install xalpha --user
    >>> import sys
    >>> sys.path.insert(0, "/home/jquser/.local/lib/python3.6/site-packages")
    >>> import xalpha as xa
    >>> xa.provider.set_jq_data(debug=True)


主要模块的关系和逻辑
---------------------
:py:mod:`xalpha.cons` 模块主要提供一些基础的函数和常量， :py:mod:`xalpha.remain` 则专门提供了一些处理分时持仓表 remtable 的函数。

:py:mod:`xalpha.record` 用于统一的处理 status 记账单，同时自身实例化可以读取 csv 文件的原有账单。且可被其他具有 status 属性的类继承，作为广泛的 status 账单处理的工具箱。 而 :py:mod:`xalpha.policy` 则用于制定虚拟的 status 记账单，来进行不同策略投资的回测，其也继承了 :class:`xalpha.record.record` 中一般的记账单处理函数。

:py:mod:`xalpha.indicator` 被具有净值表或可生成净值表的类继承，提供了一揽子净值量化分析和可视化的工具箱。其被 :class:`xalpha.info.basicinfo` 和 :class:`xalpha.multiple.mulfix` 继承和使用，后者需要通过设定 benchmark 的函数来初始化净值表。

:py:mod:`xalpha.realtime` 则是围绕基金的实时净值获取，策略集成和监视提醒为主的模块，可以用于每日按照多样的策略自动提醒投资情况。

其他四个系统的核心模块，所具有的核心数据表（都是 pandas.DataFrame 的形式），以及相互之间的关系，如下图所示。

.. image:: https://user-images.githubusercontent.com/35157286/43990032-fd6f8a3a-9d87-11e8-95c4-206b13734b40.png
 

在新版本的 xalpha 中提供了更丰富的数据抓取系统：

:py:mod:`xalpha.universal` 模块维护了不同的数据抓取，并对外提供统一的接口 :func:`xalpha.universal.get_daily` 和 :func:`xalpha.universal.get_rt`。

:py:mod:`xalpha.provider` 模块维护了需要注册的数据提供方的信息及验权接口。

:py:mod:`xalpha.toolbox` 模块维护了面向对象，封装数据的一些工具箱。


以下对象内部封装的数据结构均基于 pandas.DataFrame

*	记账单 status
*	净值表 price
*	现金流量表 cftable
*	仓位分时表 remtable


记账单格式说明
---------------------------

如果用户想一览自己的交易分析，那么记账单总是用户需要提供的，一般可以通过读取 csv 的方式导入 xalpha， 也即 ``xa.record(path)`` 即可，对于场内交易的账单，则需要 ``xa.irecord(path)``。
记账单的具体合法格式可以参考 :func:`xalpha.record.record` 的说明。


场外账单格式
++++++++++++++++

首先记账单分为场外和场内，需要提供单独的记账单。场外记账单无需提供每次申赎时的净值，因为这些值被时间唯一确定，可以智能抓取。
那么场外基金的账单，只需要时间，基金代码和数字三要素。对于数字，正数时代表申购金额，负数代表赎回份额，这与基金的申赎逻辑相符。
场外账单的默认格式是 matrix，也即每列的列头是一个不同的六位基金代码，每行的行头是一个独立的日期 (格式 20200202)，对于对应日期和基金有交易的，则在相应单元格记录数额即可 （请注意下午三点之后的申赎应算作下个交易日）。
其他单元格可为空即可。
通常可以 Excel 等记录，导出成 csv 格式即可。这一格式账单的例子可以参考 tests/demo.csv, 和 tests/demo2.csv.

场外账单的一些进阶说明：

1. 在基金代码的下一行可以额外增加 property，用于控制基金的默认交易行为。每个代码可以填写一个0到7的数字，空默认为0。其对应的交易行为是：
基金份额确认是四舍五入0 还是舍弃尾数 1， 基金是默认现金分红 0 还是分红再投 2， 基金是赎回数目对应份额 0 还是金额 4 （只支持货币基金）， property 数字为三者之和。

2. 关于交易数字的一些特别约定，交易数字小数点一位之后的非零位有特别约定，不代表交易的部分。
小数点后第二位如果是5，且当日恰好为对应基金分红日，标志着选择了分红再投入的方式，否则默认分红拿现金。（该默认行为 property 含 2 时可翻转）比如 100.05 的意思是当日分红再投入且又申购了 500 元。
对于赎回的负数，如果是一个绝对值小于 0.005 的数，标记了赎回的份额占当时总份额的比例而非赎回的份额数目， 其中-0.005对应全部赎回，线性类推。eg. -0.001对应赎回20%。

.. Note::

    如果不适应这种矩阵型的记账单，场外记账单也可以采用流水式的，也即每行记录一笔交易，列头分别是 fund，date，和 trade。这一格式的例子可以参考 tests/demo1.csv。
    此时的日期格式是 2020/2/2. 这种形式的账单，通过 ``xa.record(path, format="list")`` 来读取，不过这种账单不支持在账单层面设置基金的交易行为参数 property,
    但该参数仍可在基金投资组合 ``xa.mul(status=xa.record(path, formath="list"), property=Dict[fundcode, property_number])`` 的时候传入。对于这种格式的场外账单，
    不保证之后会维持和矩阵型场外账单同样的功能，因此请优先考虑矩阵型的场外账单格式。


场内账单格式
++++++++++++++++


场内账单则统一采用流水形式，每一笔需要记录交易净值和交易份额，此时由于买卖都是份额，因此数字全部代表份额，正买负卖，若有分红折算等，需自己手动维护，额外添加交易记录实现。
场内账单的例子请参考 tests/demo3.csv. 其列头分别是 date,code,value,share,fee。date 格式为20200202。code 对应场内代码，开头需包含 SH 或 SZ。value 是成交的净值单价。
share 代表成交的份数。fee 代表手续费，也可以不计，则默认为0，建议记录以得到交易盈利的更好全景。