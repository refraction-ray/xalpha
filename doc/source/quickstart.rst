========
快速开始
========
xalpha 可以用来对场外基金和指数进行方便的追踪和研究，
同时可以实现投资情况的汇总管理与数据分析，并且支持一些简单的基金购买策略回测。

基金和指数的信息
----------------
使用 :class:`xalpha.info.fundinfo` 来获取场外基金的基本信息和历史每日净值情况。
其中净值以 :class:`pandas.DataFrame`  的格式存储。

.. note:: 
	基金信息只支持按净值法结算的场外基金，也即大部分货币基金不被支持。

代码示例::

	>>> import xalpha as xa
	>>> zzyl = xa.fundinfo('000968') 
	>>> zzyl
	广发养老指数A
	>>> zzyl.info()
	fund name: 广发养老指数A
	fund code: 000968
	fund purchase fee: 0.12%
	fund redemption fee info: ['小于7天', '1.50%', '大于等于7天，小于1年', '0.50%', '大于等于1年，小于2年', '0.30%', '大于等于2年', '0.00%']
	>>> zzyl.price # return pandas.DataFrame object with columns date, netvalue, totalvalue and comment
	>>> zzyl.price[zzyl.price['date']<='2015-02-27']
	comment	date	netvalue	totvalue
	0	0	2015-02-13	1.0000	1.0000
	1	0	2015-02-17	1.0000	1.0000
	2	0	2015-02-27	1.0123	1.0123

使用 :class:`xalpha.info.indexinfo` 来获取相应指数的每日净值情况。

.. note::
	indexinfo() 对应的指数代码为7位数，其中后六位是正常的指数代码，第一位用来标记市场，0是沪市，1是深市。

代码示例::

	>>> zzyli = xa.indexinfo('1399812')
	>>> zzyli
	养老产业
	>>> zzyli.price[zzyli.price['date']=='2018-08-01']
		comment	date	netvalue	totvalue
	1	0	2018-08-01	7.603842	7524.4807

.. note::
	对应的 indexinfo().price 表中，netvalue 栏为以初始日归一化后的净值，而 totvalue 栏则是真实的指数值。

单一标的交易处理
-----------------
使用 :class:`xalpha.trade.trade` 来处理交易情况。
为了生成交易，需要提供标的类 :class:`xalpha.info` 和交易账单 status table。
具体的数据结构请参考高级用法 :ref:`advance`。

代码示例::

	>>>

基金投资组合的管理分析
----------------------


基金交易策略与回测
------------------


