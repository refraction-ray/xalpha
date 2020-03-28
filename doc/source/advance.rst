.. _advance:

===========
高级用法
===========

数据缓存
--------

xalpha 有两部分可以提供数据缓存和本地化。

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


第二部分本地化和缓存是专门针对 ``get_daily`` 界面的，用于存储对应的日期-价格表。这一部分的缓存和本地化更加透明。不需要任何设置，``get_daily`` 就自带内存缓存，
不会去爬取重复数据。如果想要把数据本地化存储，只需要 ``xa.set_backend(backend=, path=, prefix=, precached=)`` 即可。

其中 backend 同样可以是 csv 和 sql，也可以是默认的 memory。
path 与第一部分相同为 csv 存储的文件夹或 sql 的 engine 对象。prefix 是每个表单会添加的前缀，否则默认是用 code 做键值。
precached 可以不设，若设置为 %Y%m%d 的时间字符串格式，则代表第一次爬取就"预热"从 precached 到昨日的数据缓存。
注意到即使选取了数据库或文件作为后端，内存作为二级缓存依旧发挥作用，只要数据不改变，仍会直接读取内存数据，因此提升读写数据速度。

如果担忧内存中数据被"污染"，可以通过 ``xa.universal.check_cache(code, start, end)`` 来校验对应数据的准确性。也可用 ``xa.universal.reset_cache()`` 来清空现有的内存数据缓存。


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

xalpha 的数据来自天天基金，英为财情，雪球，彭博，标普，新浪财经，网易财经等多个源头，但有些数据还是会依赖需要鉴权的数据 API，这些被抽象成数据提供商。

比如 xalpha 的历史估值系统，依赖聚宽的数据，那么就有两种方案，
第一种是本地 ``pip install jqdatasdk`` 并且申请聚宽的本地数据试用权限（免费），
之后通过 ``xa.provider.set_jq_data(user, password)`` 即可。

如果希望不需要每次使用 xalpha 都重新鉴权，也可以在 ``set_jq_data`` 添加 ``persistent=True``
的选项，这样聚宽账户密码会简单编码后存在本地（无加密保护，请自行衡量安全性），以后每次 ``import xalpha`` 聚宽的数据源都会自动激活。

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


基金处理主要的数据结构
---------------------------

以下结构均基于 pandas.DataFrame

*	记账单 status
*	净值表 price
*	现金流量表 cftable
*	仓位分时表 remtable
