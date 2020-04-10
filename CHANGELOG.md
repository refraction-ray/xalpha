# Changelog
## Unreleased
### added
* 增加了基金详细股票和债券持仓的信息，可以通过 ``fundinfo.get_holdings(year, season)`` 调用
### fixed
* 修复了基金信息爬取的大量 corner cases, 包括 .5 年的记法，定开和封闭基金赎回费率的特殊写法，已终止基金的赎回费率处理，净值为空基金的报错，js 页面有大量换行的正则兼容

## v0.8.6 - 2020.04.09
### added
* mulfix 增加 istatus 账单读入
* get_rt 针对基金扩充更多元数据
### fixed
* 修复雪球实时HK开始的可能bug
* 今日交易记录的 trade bug

## v0.8.5 - 2020.04.08
### added
* get_bar 增加聚宽源
* get_daily 支持基金累计净值
* get_rt 返回增加时间属性
* 日线增加成交量数据（注意缓存兼容性）
* 直接将绘制 k 线图 hack 到 df 上，df.v_kline()
* 支持 dataframe web 级的显示，可用 set_display 开关
* 增加 StockPEBHistory 类可以查看个股估值历史
* 对 get_daily 增加 fetchonly 更精细的控制缓存
### fixed
* 进一步完善跨市场休市日不同时的净值预测逻辑

## v0.8.4 - 2020.04.06
### added
* 增加 vinfo 类，使得任何 get_daily 可以拿到的标的都可以进行交易。
* 增加主流市场节假日信息
* 为 get 函数增加 handler 选项，方便钩子函数嵌套
* 增加非 QDII 的溢价实时预测类 RTPredict
### changed
* xa.set_backend 也可影响 fundinfo 的缓存设定
### fixed
* 进一步完善缓存刷新掉最后一天和节假日的处理逻辑

## v0.8.3 - 2020.04.04
### added
* get_bar 增加雪球源
* 增加 set_handler
* 增加更多 FT 数据
* 增加 lru_cache_time，带 ttl 的缓存更好的防止重复爬取
### fixed
* 防止 precached 之前的日线数据无法抓取
* 为 imul 增加 istatus 关键字参数作为冗余防止误输入
* predict 对于跨市场休市更完善的考虑

## v0.8.2 - 2020.04.02
### added
* 增加聚宽宏观数据到 get_daily
* QDIIPredict 实时预测支持不同时间片混合涨幅计算
* 增加 get_bar
* 英为实时增加 app 源
* 增加日志系统，可以打印网络爬虫的详细信息
### fixed
* 增加 daily_increment 的过去选项，防止假期阻止严格检查。
* get_daily 同时兼容双向人民币中间价

## v0.8.1 - 2020.04.01
### added
* 日线增加英为 app 源备份
* 增加QDII预测的日期返回, 增加溢价率估计，增加t1计算状态
* ``set_proxy()`` 空时添加取消代理功能，和 socks5 代理支持
* ``set_holdings()`` 允许外部导入数据 py
* 增加标的对应 id 的缓存
### fixed
* 改进为实时的新浪港股 API，之前 API 存在 15分延时
* read excel 和网络下载部分解耦，增加稳定性和模块化

## v0.8.0 - 2020.03.30
## added
* 添加 ft 日线数据源和实时数据
* 将净值预测的基础设施迁移重构进 xalpha，并封装成面向对象
## fixed
* 天天基金总量 API 中，累计净值里可能存在 null
* 港股新浪实时数据现价抓取错位

## v0.7.1 - 2020.03.29
### added
* 申万行业指数历史估值情况
* cachedio 缓存器增加周末校验，周末区间自动不爬取数据
* 为 Compare 增加 col 选项，支持 close 之外的列的比较
* ``get_daily`` 新增指数总利润和净资产查看，用于更准确的刻画宏观经济
* 增加雅虎财经日线数据获取

## v0.7.0 - 2020.03.27
### changed
* 将面向对象封装的工具箱从 universal 模块移到单独的 toolbox 模块。
### added
* 增加内存缓存作为 IO 缓存的双重缓存层，提高数据读写速度。
* ``get_daily`` 增加彭博的日线数据获取。
* ``mul`` 增加 istatus 选项，可以场内外账单同时统计。
* ``get_rt`` 增加新浪实时数据源，同时增加 double_check 选项确保实时数据稳定无误。
### fixed
* 完善聚宽云平台使用的导入。

## v0.6.2 - 2020.03.25
### added
* ``set_backend`` 增加 ``precached`` 预热选项，可以一次性缓存数据备用。
* 增加 ``Compare`` 类进行不同日线的比较。

## v0.6.1 - 2020.03.25
### added
* ``get_daily`` 增加聚宽数据源的场内基金每日份额数据
* ``get_daily`` 增加标普官网数据源的各种小众标普指数历史数据

## v0.6.0 - 2020.03.24
### added
* 增加了持久化的透明缓存装饰器，用于保存平时的数据 `cachedio`，同时支持 csv，数据库或内存缓存。
* 增加了数据源提供商抽象层，并加入 jqdata 支持。
* 提供了基于 jqdata 的指数历史估值系统，和估值总结类 `PEBHistory`。

## v0.5.0 - 2020.03.21
### added
* 增加了场内数据记账单和交易的分析处理
* 增加了查看基金报告的类 FundReport
### fixed
* 爬取人民币中间价增加 UA，因为不加还是偶尔会被反爬

## v0.4.0 - 2020.03.12
### fixed
* 雪球数据获取，设定 end 之后的问题造成起点偏移，已解决。
### added
* 全新的基金特性设定接口，包括四舍五入机制，按金额赎回记录，和分红默认行为切换，均可以通过记账单第一行或 mul 类传入 property 字典来设定，且完全向后兼容。

## v0.3.2 - 2020.03.11
### fixed
* 通过 get_daily 获取的基金和雪球数据日线，不包括 end 和 start 两天，已修正为包括。
### changed
* 增加 rget 和 rpost 容错，使得 universal 部分的下载更稳定。

## v0.3.1 - 2020.03.09
### added
* 增加了 ``get_daily`` 的缓存装饰器，可以轻松无缝的缓存所有日线数据，防止反复下载

## v0.3.0 - 2020.03.08
### added
* 重磅增加几乎万能的日线数据获取器 ``get_daily``
* 增加几乎万能的实时数据获取器 ``get_rt``
### fixed
* pandas 1.0+ 的 `pandas.Timestamp` API 要求更严，bs 的 NavigableString 不被接受，需要先用 `str` 转回 python str
* day gap when incremental update: if today's data is published, add logic to avoid this
### changed
* `fundinfo` 解析网页逻辑重构，直接按字符串解析，不再引入 js parser，更加简洁, 依赖更少。

## v0.2.0 - 2020.02.19
### fixed
* 调整到支持 pyecharts 1.0+ 的可视化 API，部分可视化效果有待进一步调整
* 调整 v_tradevolume 语句顺序，避免无卖出时可视化空白的问题
* 暂时限制 pandas 为 0.x 版本，1.x 版本暂时存在时间戳转化的不兼容问题待解决
* 基金增量更新调整，防止更新区间过长时，更新数据不全的问题
* 解决 list 格式账单一天单个基金多次购买的计算 bug
* 将工作日 csv 本地化，从而绕过 tushare PRO API 需要 token 的缺点（普通 API 尚未支持 2020 年交易日数据）

## v0.1.2 - 2019.05.29
### added
* 增加了 fundinfo 和 mfundinfo 的自动选择逻辑
* 增加了新格式交易单的读取接口
* 增加了统一的异常接口
### fixed
* 暂时固定 pyecharts 为老版本（将在下一次发布时修改为支持 pyecharts 1.0+）
* fundinfo 增量更新，指定为货币基金代码的时候，可以妥善地报异常

## v0.1.1 - 2018.12.29
### changed
* 更简洁的底层逻辑，用来处理多个基金日期不完全相同的情形
### fixed
* 对于基金类增量更新的 API 中注释栏的处理进行了完善

## v0.1.0 - 2018.08.20
### added
* record 类增加 save_csv 函数，将账单一键保存
* info 各个类增加了增量更新的逻辑，可以将数据本地化到 csv 文件，大幅提升了速度
* info 类的增量更新亦可选择任意 sqlalchemy 支持连接的数据库，将数据本地化
### fixed
* 进一步校正 trade 类 dailyreport 在未发生过交易时的展示逻辑

## v0.0.7 - 2018.08.17
### added
* indicator 模块增加了大量技术面指标的计算工具，并针对性的设计了新的可视化函数
* 增加了基于不同技术指标交叉或点位触发的交易策略
### fixed
* 将时间常量修改为函数
* 注意到 QDII 基金可能在美国节假日无净值，从而造成和国内基金净值天数不同的问题，修复了在 evaluate 模块这部分的处理逻辑
* 解决部分可视化函数字典参数传入不到位问题

## v0.0.6 - 2018.08.14
### added
* 新增真实的货币基金类 mfundinfo，与虚拟货币基金类 cashinfo 互为补充
* 新增了 realtime 模块，可以根据存储制定的策略，提供实时的投资建议，并自动发送邮件通知
### fixed
* info 类赎回逻辑的进一步完善，未来赎回则视为最后一个有记录的净值日赎回
* info 类故意屏蔽掉今天的净值，即使净值已更新，防止出现各种逻辑错误
* 完善 policy 的各个子类，使其对未来测试兼容

## v0.0.5 - 2018.08.12 
### added
* mul 类增加返回 evaluate 对象的函数
* 增加了新的模块 evaluate 类，可以作为多净值系统的比较分析工具，现在提供净值可视化与相关系数分析的功能
### fixed
* 基金组合总收益率展示改为以百分之一为单位
* 交易类的成本曲线可视化改为自有交易记录开始
* 对于 fundinfo 的处理逻辑更加完善，进一步扩大了对各种情形处理的考量
* 完善 trade 类中各量计算时，早于基金成立日的处理逻辑

## v0.0.4 - 2018.08.09
### added
* policy 模块增加网格交易类，以进行波段网格交易的回测分析和指导
* 更直接的一键虚拟清仓功能添加到 record 类，并将具有 status 的类都视为有 record 的 MixIn
* v_tradevolume() 这一基于现金表的可视化函数，增加了 freq＝ 的关键字参数，可选 D，W，M，从而直接展示不同时间为单位的交易总量柱形图

### changed
* 修改了基金收益率的计算逻辑，大幅重构了 dailyreport 的内容和计算，并引入了简单的换手率指标估算

### deprecated
* 鉴于 mul 类中 combsummary 函数展示数据的完整度很高，tot函数不再推荐使用

## v0.0.3 - 2018.08.06
### added
* 增加基于现金流量表的成交量柱形图可视化
* 增加 mul 类的 combsummary 展示总结函数
* policy 增加了可以定期不定额投资的 scheduled_tune 类

### fixed
* 可视化函数绘图关键词传入的修正
* policy 类生成投资 status 时遍历所有时间而非只交易日
* 注意了 fundinfo 类中时间戳读取的时区问题，使得程序可以在不同系统时间得到正确结果

## v0.0.2 - 2018.08.03
### added
* 配置 setup.py，使得通过 pip 安装可以自动安装依赖，注意 ply 库采用了老版本 3.4，这是为了防止调用 slimit 库时不必要的报 warning