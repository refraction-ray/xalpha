# -*- coding: utf-8 -*-
"""
modules for Object oriented toolbox which wrappers get_daily and some more
"""

import datetime as dt
import numpy as np
import pandas as pd
from xalpha.cons import opendate, yesterday
from xalpha.universal import get_rt, _convert_code, _inverse_convert_code
import xalpha.universal as xu  ## 为了 set_backend 可以动态改变此模块的 get_daily


class PEBHistory:
    """
    对于指数历史 PE PB 的封装类
    """

    indexs = {
        "000016.XSHG": ("上证50", "2012-01-01"),
        "000300.XSHG": ("沪深300", "2012-01-01"),
        "000905.XSHG": ("中证500", "2012-01-01"),
        "000922.XSHG": ("中证红利", "2012-01-01"),
        "399006.XSHE": ("创业板指", "2012-01-01"),
        "000992.XSHG": ("全指金融", "2012-01-01"),
        "000991.XSHG": ("全指医药", "2012-01-01"),
        "399932.XSHE": ("中证消费", "2012-01-01"),
        "000831.XSHG": ("500低波", "2013-01-01"),
        "000827.XSHG": ("中证环保", "2013-01-01"),
        "000978.XSHG": ("医药100", "2012-01-01"),
        "399324.XSHE": ("深证红利", "2012-01-01"),
        "399971.XSHE": ("中证传媒", "2014-07-01"),
        "000807.XSHG": ("食品饮料", "2013-01-01"),
        "000931.XSHG": ("中证可选", "2012-01-01"),
        "399812.XSHE": ("养老产业", "2016-01-01"),
        "000852.XSHG": ("中证1000", "2015-01-01"),
    }

    # 聚宽数据源支持的指数列表： https://www.joinquant.com/indexData

    def __init__(self, code, start=None, end=None):
        """

        :param code: str. 形式可以是 399971.XSHE 或者 SH000931
        :param start: Optional[str]. %Y-%m-%d, 估值历史计算的起始日。
        :param end: Dont use, only for debug
        """
        yesterday_str = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
        if len(code.split(".")) == 2:
            self.code = code
            self.scode = _convert_code(code)
        else:
            self.scode = code
            self.code = _inverse_convert_code(self.scode)
        if self.code in self.indexs:
            self.name = self.indexs[self.code][0]
            if not start:
                start = self.indexs[self.code][1]
        else:
            try:
                self.name = get_rt(self.scode)["name"]
            except:
                self.name = self.scode
            if not start:
                start = "2012-01-01"  # 可能会出问题，对应指数还未有数据
        self.start = start
        if not end:
            end = yesterday_str
        self.df = xu.get_daily("peb-" + self.scode, start=self.start, end=end)
        self.ratio = None
        self.pep = [
            round(i, 3) for i in np.percentile(self.df.pe, np.arange(0, 110, 10))
        ]
        self.pbp = [
            round(i, 3) for i in np.percentile(self.df.pb, np.arange(0, 110, 10))
        ]

    def percentile(self):
        """
        打印 PE PB 的历史十分位对应值

        :return:
        """
        print("PE 历史分位:\n")
        print(*zip(np.arange(0, 110, 10), self.pep), sep="\n")
        print("\nPB 历史分位:\n")
        print(*zip(np.arange(0, 110, 10), self.pbp), sep="\n")

    def v(self, y="pe"):
        """
        pe 或 pb 历史可视化

        :param y: Optional[str]. "pe" (defualt) or "pb"
        :return:
        """
        return self.df.plot(x="date", y=y)

    def fluctuation(self):
        if not self.ratio:
            d = self.df.iloc[-1]["date"]
            oprice = xu.get_daily(
                code=self.scode, end=d.strftime("%Y%m%d"), prev=20
            ).iloc[-1]["close"]
            nprice = get_rt(self.scode)["current"]
            self.ratio = nprice / oprice
        return self.ratio

    def current(self, y="pe"):
        """
        返回实时的 pe 或 pb 绝对值估计。

        :param y: Optional[str]. "pe" (defualt) or "pb"
        :return: float.
        """
        return round(self.df.iloc[-1][y] * self.fluctuation(), 3)

    def current_percentile(self, y="pe"):
        """
        返回实时的 pe 或 pb 历史百分位估计

        :param y: Optional[str]. "pe" (defualt) or "pb"
        :return: float.
        """
        df = self.df
        d = len(df)
        u = len(df[df[y] < self.current(y)])
        return round(u / d * 100, 2)

    def summary(self):
        """
        打印现在估值的全部分析信息。

        :return:
        """
        print("指数%s估值情况\n" % self.name)
        if dt.datetime.strptime(self.start, "%Y-%m-%d") > dt.datetime(2015, 1, 1):
            print("(历史数据较少，仅供参考)\n")
        #         self.percentile()
        print(
            "现在 PE 绝对值 %s, 相对分位 %s%%，距离最低点 %s %%\n"
            % (
                self.current("pe"),
                self.current_percentile("pe"),
                max(
                    round(
                        (self.current("pe") - self.pep[0]) / self.current("pe") * 100, 1
                    ),
                    0,
                ),
            )
        )
        print(
            "现在 PB 绝对值 %s, 相对分位 %s%%，距离最低点 %s %%\n"
            % (
                self.current("pb"),
                self.current_percentile("pb"),
                max(
                    round(
                        (self.current("pb") - self.pbp[0]) / self.current("pb") * 100, 1
                    ),
                    0,
                ),
            )
        )


class Compare:
    """
    将不同金融产品同起点归一化比较
    """

    def __init__(self, *codes, start="20200101", end=yesterday()):
        """

        :param codes: Union[str, tuple], 格式与 :func:`xalpha.universal.get_daily` 相同，若需要汇率转换，需要用 tuple，第二个元素形如 "USD"
        :param start: %Y%m%d
        :param end: %Y%m%d, default yesterday
        """
        totdf = pd.DataFrame()
        codelist = []
        for c in codes:
            if isinstance(c, tuple):
                code = c[0]
                currency = c[1]
            else:
                code = c
                currency = "CNY"  # 标的不做汇率调整
            codelist.append(code)
            df = xu.get_daily(code, start=start, end=end)
            df = df[df.date.isin(opendate)]
            if currency != "CNY":
                cdf = xu.get_daily(currency + "/CNY", start=start, end=end)
                cdf = cdf[cdf["date"].isin(opendate)]
                df = df.merge(right=cdf, on="date", suffixes=("_x", "_y"))
                df["close"] = df["close_x"] * df["close_y"]
            df[code] = df["close"] / df.iloc[0].close
            df = df.reset_index()
            df = df[["date", code]]
            if "date" not in totdf.columns:
                totdf = df
            else:
                totdf = totdf.merge(on="date", right=df)
        self.totdf = totdf
        self.codes = codelist

    def v(self):
        """
        显示日线可视化

        :return:
        """
        return self.totdf.plot(x="date", y=self.codes)

    def corr(self):
        """
        打印相关系数矩阵

        :return: pd.DataFrame
        """
        return self.totdf.iloc[:, 1:].pct_change().corr()
