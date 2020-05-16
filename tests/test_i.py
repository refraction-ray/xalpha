"""
对于场内数据相关基础设施的测试
"""

import sys

sys.path.insert(0, "../")
import xalpha as xa
import pandas as pd

path3 = "demo3.csv"
path = "demo.csv"
ioconf = {"save": True, "fetch": True, "path": "pytest", "form": "csv"}
ir = xa.irecord(path3)
orc = xa.record(path)


def test_irecord():
    assert len(ir.filter("SH501018")) == 8


def test_itrade():
    t = xa.itrade("SH512880", ir)
    assert round(t.xirrrate("20200313"), 2) == 12.49
    assert t.dailyreport().iloc[0]["基金名称"] == "证券ETF"


def test_imul():
    c = xa.imul(status=ir)
    assert round(c.combsummary("20200309").iloc[0]["投资收益率"], 2) == -1.39
    c.v_positions()
    c = xa.mul(status=orc, istatus=ir, **ioconf)
    assert round(c.combsummary("20200309").iloc[0]["投资收益率"], 2) == 0.49
    c.v_category_positions()
    c.get_stock_holdings(date="2020-04-08")
    c.get_portfolio(date="20200501")


def test_imulfix():
    c = xa.mulfix(status=orc, istatus=ir, totmoney=100000, **ioconf)
    c.summary()
    c.v_category_positions("2020-04-08")
    c.get_stock_holdings()
    c.get_portfolio(date="20200501")
