
# Changelog

## unreleased

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
* 配置 setup.py，使得通过 pip 安装可以自动安装依赖，注意 ply 库采用了老版本 3.4，这是为了防止调用 slimit 库是不必要的报 warning。