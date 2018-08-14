.. _advance:

===========
高级用法
===========

主要模块的关系和逻辑
---------------------
:py:mod:`xalpha.cons` 模块主要提供一些基础的函数和常量， :py:mod:`xalpha.remain` 则专门提供了一些处理分时持仓表 remtable 的函数。

:py:mod:`xalpha.record` 用于统一的处理 status 记账单，同时自身实例化可以读取 csv 文件的原有账单。且可被其他具有 status 属性的类继承，作为广泛的 status 账单处理的工具箱。 而 :py:mod:`xalpha.policy` 则用于制定虚拟的 status 记账单，来进行不同策略投资的回测，其也继承了 :class:`xalpha.record.record` 中一般的记账单处理函数。

:py:mod:`xalpha.indicator` 被具有净值表或可生成净值表的类继承，提供了一揽子净值量化分析和可视化的工具箱。其被 :class:`xalpha.info.basicinfo` 和 :class:`xalpha.multiple.mulfix` 继承和使用，后者需要通过设定 benchmark 的函数来初始化净值表。

:py:mod:`xalpha.realtime` 则是围绕基金的实时净值获取，策略集成和监视提醒为主的模块，可以用于每日按照多样的策略自动提醒投资情况。

其他四个系统的核心模块，所具有的核心数据表（都是 pandas.DataFrame 的形式），以及相互之间的关系，如下图所示。

.. image:: https://user-images.githubusercontent.com/35157286/43990032-fd6f8a3a-9d87-11e8-95c4-206b13734b40.png
 


主要的数据结构
----------------

*	记账单 status
*	净值表 price
*	现金流量表 cftable
*	仓位分时表 remtable
