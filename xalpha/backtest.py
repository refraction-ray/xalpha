# -*- coding: utf-8 -*-
"""
modules for dynamical backtesting framework
"""

import pandas as pd

from xalpha.info import fundinfo, mfundinfo
from xalpha.trade import trade
from xalpha.multiple import mul, mulfix
from xalpha.cons import yesterdayobj
from xalpha.exceptions import TradeBehaviorError, FundTypeError
from xalpha.cons import opendate_set, next_onday, convert_date


class GlobalRegister:
    def __init__(self):
        pass


class BTE:
    """
    BackTestEnvironment, currently only fund is supported

    """

    def __init__(self, start, end=None, totmoney=1000000, verbose=False, **kws):
        self.start = convert_date(start)
        self.verbose = verbose
        self.kws = kws
        self.totmoney = totmoney
        self.g = GlobalRegister()
        self.trades = {}  # codes: infoobj
        self.infos = {}  # codes: infoobj
        self.lastdates = {}  # codes: date
        if end is None:
            end = yesterdayobj()
        self.end = end
        self.sys = None

    def prepare(self):
        pass

    def run(self):
        raise NotImplementedError("Please implement your `run` function in your class")

    def backtest(self):
        self.prepare()
        dates = pd.bdate_range(self.start, self.end)
        for d in dates:
            self.run(d)

    def get_current_mul(self):
        if self.trades:
            return mul(*[v for _, v in self.trades.items()])
        else:
            return

    def get_current_mulfix(self):
        if self.trades:
            return mulfix(*[v for _, v in self.trades.items()], totmoney=self.totmoney)
        else:
            return

    def set_fund(self, code, value_label=0, round_label=0, dividend_label=0):
        if code in self.infos:
            self.infos[code].value_lable = value_label
            self.infos[code].round_lable = round_label
            self.infos[code].dividend_lable = dividend_label
        else:
            self.infos[code] = self.get_info(code)
            self.infos[code].value_lable = value_label
            self.infos[code].round_lable = round_label
            self.infos[code].dividend_lable = dividend_label

    def get_info(self, code):
        try:
            return fundinfo(code[1:])
        except FundTypeError:
            return mfundinfo(code[1:])

    def buy(self, code, value, date, is_value=True):
        if self.verbose:
            print(f"buy {value} of {code} on {date.strftime('%Y-%m-%d')}")
        if code in self.trades:
            df = self.trades[code].status
            cftable = self.trades[code].cftable
            cftable = cftable[cftable["date"] <= self.lastdates[code]]
            remtable = self.trades[code].remtable
            remtable = remtable[remtable["date"] <= self.lastdates[code]]
            self.lastdates[code] = date
            df2 = pd.DataFrame([[date, value]], columns=["date", code[1:]])
            df = df.append(df2)
            self.trades[code] = trade(
                self.infos[code], df, cftable=cftable, remtable=remtable,
            )
        else:
            self.lastdates[code] = date
            if code not in self.infos:
                self.infos[code] = self.get_info(code)
            df = pd.DataFrame({"date": [date], code[1:]: [value]})
            self.trades[code] = trade(self.infos[code], df)

    def sell(self, code, share, date, is_value=False):
        share = abs(share)
        if self.verbose:
            print(f"sell {share} of {code} on {date.strftime('%Y-%m-%d')}")
        if code not in self.trades:
            raise TradeBehaviorError("You are selling something that you don't have")
        df = self.trades[code].status
        cftable = self.trades[code].cftable
        cftable = cftable[cftable["date"] <= self.lastdates[code]]
        remtable = self.trades[code].remtable
        remtable = remtable[remtable["date"] <= self.lastdates[code]]
        self.lastdates[code] = date
        self.lastdates[code] = date
        df2 = pd.DataFrame([[date, -share]], columns=["date", code[1:]])
        df = df.append(df2)
        if is_value:
            self.set_fund(code, value_label=1)
        self.trades[code] = trade(
            self.infos[code], df, cftable=cftable, remtable=remtable,
        )
        if is_value:
            self.set_fund(code, value_label=0)


## the following are some example backtest policy classes for testing and educational purpose
## they are not stable in terms of API, and don't rely on them in production environment


class Scheduled(BTE):
    def prepare(self):
        self.code = self.kws["code"]
        self.value = self.kws["value"]  # 每次投入金额
        self.date_range = self.kws["date_range"]  # pd.data_range 买入日期列表

    def run(self, date):
        if date in self.date_range:
            if date in opendate_set:
                self.buy(self.code, self.value, date)
            else:
                date = next_onday(date)
                self.buy(self.code, self.value, date)


class AverageScheduled(Scheduled):
    def prepare(self):
        super().prepare()
        self.aim = 0
        self.infos[self.code] = self.get_info(self.code)

    def run(self, date):
        if date in self.date_range:
            self.aim += self.value
            sys = self.get_current_mul()
            if sys is not None:
                sys = sys.summary(date.strftime("%Y-%m-%d"))
                row = sys[sys["基金名称"] == "总计"].iloc[0]
                current = row["基金现值"]
            else:
                current = 0
            if date not in opendate_set:
                date = next_onday(date)
            if self.aim > current:
                self.buy(self.code, self.aim - current, date)
            else:
                df = self.infos[self.code].price
                unitvalue = df[df["date"] >= date].iloc[0].netvalue
                self.sell(self.code, (current - self.aim) / unitvalue, date)


class ScheduledSellonXIRR(Scheduled):
    def prepare(self):
        super().prepare()
        self.sold = False
        self.threhold = self.kws.get("threhold", 0.2)
        self.holding_time = self.kws.get("holding_time", 180)
        # 定投开始一定时间后，才按照年化判断退出时机

    def run(self, date):
        if (
            date.weekday() == 4
            and not self.sold
            and (date - self.start).days > self.holding_time
        ):  #  每周只检查一次退出条件
            sys = self.get_current_mul()
            if sys is not None:
                try:
                    xirr = sys.xirrrate(date=date.strftime("%Y-%m-%d"))
                except RuntimeError:
                    xirr = 0.0
                if self.verbose:
                    print(f"{date.strftime('%Y-%m-%d')} 内部年化收益率为 {round(xirr*100, 0)}%")
                if xirr > self.threhold:
                    self.sold = True
                    self.sell(self.code, -0.005, date)
        if not self.sold:
            super().run(date)
