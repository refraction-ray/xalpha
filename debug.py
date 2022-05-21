import logging
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Pie, ThemeRiver

from xalpha.cons import convert_date, myround, yesterdaydash, yesterdayobj
from xalpha.evaluate import evaluate
from xalpha.exceptions import FundTypeError, TradeBehaviorError
from xalpha.record import record, irecord
from xalpha.indicator import indicator
from xalpha.info import cashinfo, fundinfo, mfundinfo, get_fund_holdings
from xalpha.trade import (
    bottleneck,
    trade,
    turnoverrate,
    vtradevolume,
    xirrcal,
    itrade,
    vtradecost,
)
from xalpha.multiple import mul,mulfix
from xalpha.universal import get_fund_type, ttjjcode, get_rt, get_industry_fromxq
import xalpha.universal as xu

#status = pd.DataFrame([
#    ['2019-12-31',-0.04],
#    ['2020-06-09',2738.22],
#    ['2020-08-05',3668.81],
#    ['2020-08-10',793.97],
#    ['2020-12-31',83.93],
#    ['2021-12-16',1271.55],
#    ['2021-12-31',111.29]
#],columns=['date','mf'])
#status["date"] = pd.to_datetime(status['date'])
#cashobj = cashinfo(start='2019-04-24')
#trade(cashobj,status)

status = pd.DataFrame([
    ['2012-02-17',100000.0],
    ['2012-03-15',-0.005],
    ['2012-03-27',103902.230],
    ['2012-03-29',-0.005],
],columns=['date','159915'])
status["date"] = pd.to_datetime(status['date'])
infoobj = fundinfo('F159915')
trade(infoobj,status)