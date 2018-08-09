# Changelog

## unreleased

## v0.0.4 - 2018.08.09
### added
* policy 模块增加网格交易类，以进行波段网格交易的回测分析和指导
* 更直接的一键虚拟清仓功能添加到 record 类，并将具有 status 的类都视为有 record 的 Mix
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
* 配置 setup.py，使得通过 pip 安装可以自动安装依赖，注意 ply 库采用了老版本 3.4，这是为了防止调用 slimit 库时不必要的报 warning。