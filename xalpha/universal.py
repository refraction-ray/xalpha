# -*- coding: utf-8 -*-
"""
modules for universal fetcher that gives historical daily data and realtime data
for almost everything in the market
"""

import os
import sys
import time
import datetime as dt
import numpy as np
import pandas as pd
import logging
import inspect
from bs4 import BeautifulSoup
from functools import wraps, lru_cache
from uuid import uuid4
from sqlalchemy import exc
from dateutil.relativedelta import relativedelta

try:
    from jqdatasdk import (
        get_index_weights,
        query,
        get_fundamentals,
        valuation,
        get_query_count,
        finance,
        get_index_stocks,
        macro,
    )

    # 本地导入
except ImportError:
    try:
        from jqdata import finance, macro  # 云平台导入
    except ImportError:
        pass

from xalpha.info import basicinfo, fundinfo, mfundinfo
from xalpha.indicator import indicator
from xalpha.cons import (
    rget,
    rpost,
    rget_json,
    rpost_json,
    tz_bj,
    today_obj,
    region_trans,
)
from xalpha.provider import data_source
from xalpha.exceptions import DataPossiblyWrong, ParserFailure

pd.options.mode.chained_assignment = None  # turn off setwith copy warning
thismodule = sys.modules[__name__]
xamodule = sys.modules["xalpha"]
logger = logging.getLogger(__name__)


def tomorrow_ts():
    dto = dt.datetime.now() + dt.timedelta(1)
    return dto.timestamp()


def has_weekday(start, end):
    for d in pd.date_range(start, end):
        if d.weekday() < 5:
            return True
    return False


def lru_cache_time(ttl=None, maxsize=None):
    """
    TTL support on lru_cache

    :param ttl: float or int, seconds
    :param maxsize: int, maxsize for lru_cache
    :return:
    """

    def wrapper(func):
        # Lazy function that makes sure the lru_cache() invalidate after X secs
        @lru_cache(maxsize)
        def time_aware(_ttl, *args, **kwargs):
            return func(*args, **kwargs)

        setattr(thismodule, func.__name__ + "_ttl", time_aware)

        @wraps(func)
        def newfunc(*args, **kwargs):
            ttl_hash = round(time.time() / ttl)
            f_ttl = getattr(thismodule, func.__name__ + "_ttl")
            return f_ttl(ttl_hash, *args, **kwargs)

        return newfunc

    return wrapper


# TODO: 缓存 token 的合适时间尺度
@lru_cache_time(ttl=300)
def get_token():
    """
    获取雪球的验权 token，匿名也可获取，而且似乎永远恒定(大时间范围内会改变)

    :return:
    """
    r = rget("https://xueqiu.com", headers={"user-agent": "Mozilla"})
    return r.cookies["xq_a_token"]


def get_history(
    code, prefix="SH", count=365, token="a664afb60c7036c7947578ac1a5860c4cfb6b3b5"
):
    url = "https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol={prefix}{code}&begin={tomorrow}&period=day&type=before&count=-{count}"
    data = rget_json(
        url.format(
            code=code, prefix=prefix, tomorrow=int(tomorrow_ts() * 1000), count=count
        ),
        cookies={"xq_a_token": token},
        headers={"user-agent": "Mozilla/5.0"},
    )
    return data


def ts2pdts(ts):
    dto = dt.datetime.fromtimestamp(ts / 1000, tz=tz_bj).replace(tzinfo=None)
    return dto.replace(
        hour=0, minute=0, second=0, microsecond=0
    )  # 雪球美股数据时间戳是美国0点，按北京时区换回时间后，把时分秒扔掉就重合了


def get_historical_fromxq(code, count):
    r = get_history(code=code, prefix="", count=count, token=get_token())
    df = pd.DataFrame(data=r["data"]["item"], columns=r["data"]["column"])
    df["date"] = (df["timestamp"]).apply(ts2pdts)  # reset hours to zero
    return df


def get_historical_fromcninvesting(curr_id, st_date, end_date, app=False):
    data = {
        "curr_id": curr_id,
        #  "smlID": smlID,  # ? but seems to be fixed with curr_id, it turns out it doesn't matter
        "st_date": st_date,  # %Y/%m/%d
        "end_date": end_date,
        "interval_sec": "Daily",
        "sort_col": "date",
        "sort_ord": "DESC",
        "action": "historical_data",
    }
    if not app:  # fetch from web api
        r = rpost(
            "https://cn.investing.com/instruments/HistoricalDataAjax",
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4)\
                    AppleWebKit/537.36 (KHTML, like Gecko)",
                "Host": "cn.investing.com",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
    else:  # fetch from app api
        r = rpost(
            "https://cnappapi.investing.com/instruments/HistoricalDataAjax",
            data=data,
            headers={
                "Accept": "*/*",
                "Accept-Encoding": "gzip",
                "Accept-Language": "zh-cn",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "User-Agent": "Investing.China/0.0.3 CFNetwork/1121.2.2 Darwin/19.3.0",
                "ccode": "CN",
                #'ccode_time': '1585551041.986028',
                "x-app-ver": "117",
                "x-meta-ver": "14",
                "x-os": "ios",
                "x-uuid": str(uuid4()),
                "Host": "cn.investing.com",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
    s = BeautifulSoup(r.text, "lxml")
    dfdict = {}
    cols = []
    for col in s.find_all("th"):
        dfdict[str(col.contents[0])] = []
        cols.append(str(col.contents[0]))
    num_cols = len(cols)
    for i, td in enumerate(s.find_all("td")[:-5]):
        if cols[i % num_cols] == "日期":
            dfdict[cols[i % num_cols]].append(
                dt.datetime.strptime(str(td.string), "%Y年%m月%d日")
            )
        else:
            dfdict[cols[i % num_cols]].append(str(td.string))
    return pd.DataFrame(dfdict)


def prettify(df):
    _map = {
        "日期": "date",
        "收盘": "close",
        "开盘": "open",
        "高": "high",
        "低": "low",
        "涨跌幅": "percent",
    }
    df.rename(_map, axis=1, inplace=True)
    if len(df) > 1 and df.iloc[1]["date"] < df.iloc[0]["date"]:
        df = df[::-1]
    df = df[["date", "open", "close", "high", "low", "percent"]]
    for k in ["open", "close", "high", "low"]:
        df[k] = df[k].apply(_float)
    return df


def dstr2dobj(dstr):
    if len(dstr.split("/")) > 1:
        d_obj = dt.datetime.strptime(dstr, "%Y/%m/%d")
    elif len(dstr.split(".")) > 1:
        d_obj = dt.datetime.strptime(dstr, "%Y.%m.%d")
    elif len(dstr.split("-")) > 1:
        d_obj = dt.datetime.strptime(dstr, "%Y-%m-%d")
    else:
        d_obj = dt.datetime.strptime(dstr, "%Y%m%d")
    return d_obj


@lru_cache(maxsize=1024)
def get_investing_id(suburl, app=False):
    if not app:
        url = "https://cn.investing.com"
    else:
        url = "https://cnappapi.investing.com"
    if not suburl.startswith("/"):
        url += "/"
    url += suburl
    if not app:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36"
        }
    else:
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Accept-Language": "zh-cn",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "User-Agent": "Investing.China/0.0.3 CFNetwork/1121.2.2 Darwin/19.3.0",
            "ccode": "CN",
            #'ccode_time': '1585551041.986028',
            "x-app-ver": "117",
            "x-meta-ver": "14",
            "x-os": "ios",
            "x-uuid": str(uuid4()),
            "Host": "cn.investing.com",
            "X-Requested-With": "XMLHttpRequest",
        }
    r = rget(url, headers=headers,)
    s = BeautifulSoup(r.text, "lxml")
    pid = s.find("span", id="last_last")["class"][-1].split("-")[1]
    return pid


def _variate_ua():
    last = 20 + np.random.randint(20)
    ua = []
    ua.append(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko)"
    )
    ua.append(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
    )
    choice = np.random.randint(2)
    return ua[choice][:last]


@lru_cache_time(ttl=120, maxsize=128)
def get_rmb(start=None, end=None, prev=360, currency="USD/CNY"):
    """
    获取人民币汇率中间价, 该 API 官网数据源，稳定性很差

    :param start:
    :param end:
    :param prev:
    :param currency:
    :return: pd.DataFrame
    """
    bl = ["USD", "EUR", "100JPY", "HKD", "GBP", "AUD", "NZD", "SGD", "CHF", "CAD"]
    al = [
        "MYR",
        "RUB",
        "ZAR",
        "KRW",
        "AED",
        "SAR",
        "HUF",
        "PLN",
        "DKK",
        "SEK",
        "NOK",
        "TRY",
        "MXN",
        "THB",
    ]
    is_inverse = False
    if (currency[:3] in al) or (currency[4:] in bl):
        is_inverse = True
        currency = currency[4:] + "/" + currency[:3]
    url = "http://www.chinamoney.com.cn/ags/ms/cm-u-bk-ccpr/CcprHisNew?startDate={start_str}&endDate={end_str}&currency={currency}&pageNum=1&pageSize=300"
    if not end:
        end_obj = today_obj()
    else:
        end_obj = dstr2dobj(end)
    if not start:
        start_obj = end_obj - dt.timedelta(prev)
    else:
        start_obj = dstr2dobj(start)
    start_str = start_obj.strftime("%Y-%m-%d")
    end_str = end_obj.strftime("%Y-%m-%d")
    count = (end_obj - start_obj).days + 1
    rl = []
    # API 很奇怪，需要经常变 UA 才好用

    headers = {
        "Referer": "http://www.chinamoney.com.cn/chinese/bkccpr/",
        "Origin": "http://www.chinamoney.com.cn",
        "Host": "www.chinamoney.com.cn",
        "X-Requested-With": "XMLHttpRequest",
    }

    if count <= 360:
        headers.update({"user-agent": _variate_ua()})
        r = rpost_json(
            url.format(start_str=start_str, end_str=end_str, currency=currency),
            headers=headers,
        )
        rl.extend(r["records"])
    else:  # data more than 1 year cannot be fetched once due to API limitation
        sepo_obj = end_obj
        sepn_obj = sepo_obj - dt.timedelta(360)
        #         sep0_obj = end_obj - dt.timedelta(361)
        while sepn_obj > start_obj:  # [sepn sepo]
            headers.update({"user-agent": _variate_ua()})
            r = rpost_json(
                url.format(
                    start_str=sepn_obj.strftime("%Y-%m-%d"),
                    end_str=sepo_obj.strftime("%Y-%m-%d"),
                    currency=currency,
                ),
                headers=headers,
            )
            rl.extend(r["records"])

            sepo_obj = sepn_obj - dt.timedelta(1)
            sepn_obj = sepo_obj - dt.timedelta(360)
        headers.update({"user-agent": _variate_ua()})
        r = rpost_json(
            url.format(
                start_str=start_obj.strftime("%Y-%m-%d"),
                end_str=sepo_obj.strftime("%Y-%m-%d"),
                currency=currency,
            ),
            headers=headers,
        )
        rl.extend(r["records"])
    data = {"date": [], "close": []}
    for d in rl:
        data["date"].append(pd.Timestamp(d["date"]))
        data["close"].append(d["values"][0])
    df = pd.DataFrame(data)
    df = df[::-1]
    df["close"] = pd.to_numeric(df["close"])
    if is_inverse:
        df["close"] = 1 / df["close"]
    return df


def get_fund(code):
    # 随意设置非空 path，防止嵌套缓存到 fundinfo
    if code[0] == "F":
        df = fundinfo(code[1:], path="nobackend").price
    elif code[0] == "M":
        df = mfundinfo(code[1:], path="nobackend").price
    df["close"] = df["netvalue"]
    return df[["date", "close"]]


# this is the most elegant approach to dispatch get_daily, the definition can be such simple
# you actually don't need to bother on start end blah, everything is taken care of by ``cahcedio``
@data_source("jq")
def get_fundshare_byjq(code, **kws):
    code = _inverse_convert_code(code)
    df = finance.run_query(
        query(finance.FUND_SHARE_DAILY)
        .filter(finance.FUND_SHARE_DAILY.code == code)
        .filter(finance.FUND_SHARE_DAILY.date >= kws["start"])
        .filter(finance.FUND_SHARE_DAILY.date <= kws["end"])
        .order_by(finance.FUND_SHARE_DAILY.date)
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", "shares"]]
    return df


def get_historical_fromsp(code, start=None, end=None, **kws):
    """
    标普官网数据源

    :param code:
    :param start:
    :param end:
    :param kws:
    :return:
    """

    if code.startswith("SP"):
        code = code[2:]
    if len(code.split(".")) > 1:
        col = code.split(".")[1]
        code = code.split(".")[0]
    else:
        col = "1"
    start_obj = dt.datetime.strptime(start, "%Y%m%d")
    today_obj = dt.datetime.now()
    fromnow = (today_obj - start_obj).days
    if fromnow < 300:
        flag = "one"
    elif fromnow < 1000:
        flag = "three"
    else:
        flag = "ten"
    url = "https://us.spindices.com/idsexport/file.xls?\
selectedModule=PerformanceGraphView&selectedSubModule=Graph\
&yearFlag={flag}YearFlag&indexId={code}".format(
        flag=flag, code=code
    )
    r = rget(url)
    df = pd.read_excel(r.content)
    # print(df.iloc[:10])
    df = df.iloc[6:]
    df["close"] = df["Unnamed: " + col]
    df["date"] = pd.to_datetime(df["Unnamed: 0"])
    df = df[["date", "close"]]
    return df


def get_historical_frombb(code, start=None, end=None, **kws):
    """
    https://www.bloomberg.com/ 数据源, 试验性支持。
    似乎有很严格的 IP 封禁措施, 且最新数据更新滞后，且国内会被 reset，似乎难以支持 T-1 净值预测。强烈建议从英为或雅虎能找到的标的，不要用彭博源，该 API 只能作为 last resort。

    :param code:
    :param start:
    :param end:
    :param kws:
    :return:
    """
    if code.startswith("BB-"):
        code = code[3:]
    # end_obj = dt.datetime.strptime(end, "%Y%m%d")
    start_obj = dt.datetime.strptime(start, "%Y%m%d")
    today_obj = dt.datetime.now()
    fromnow = (today_obj - start_obj).days
    if fromnow < 20:
        years = "1_MONTH"
    elif fromnow < 300:
        years = "1_YEAR"
    else:
        years = "5_YEAR"
    url = "https://www.bloomberg.com/markets2/api/history/{code}/PX_LAST?\
timeframe={years}&period=daily&volumePeriod=daily".format(
        years=years, code=code
    )
    r = rget_json(
        url,
        headers={
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko)",
            "referer": "https://www.bloomberg.com/quote/{code}".format(code=code),
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "accept": "*/*",
        },
    )
    df = pd.DataFrame(r[0]["price"])
    df["close"] = df["value"]
    df["date"] = pd.to_datetime(df["dateTime"])
    df = df[["date", "close"]]
    return df


def get_historical_fromft(code, start, end, _type="indices"):
    """
    finance times 数据

    :param code:
    :param start:
    :param end:
    :return:
    """
    if not code.isdigit():
        code = get_ft_id(code, _type=_type)
    start = start.replace("/", "").replace("-", "")
    end = end.replace("/", "").replace("-", "")
    start = start[:4] + "/" + start[4:6] + "/" + start[6:]
    end = end[:4] + "/" + end[4:6] + "/" + end[6:]
    url = "https://markets.ft.com/data/equities/ajax/\
get-historical-prices?startDate={start}&endDate={end}&symbol={code}".format(
        code=code, start=start, end=end
    )
    r = rget_json(url, headers={"user-agent": "Mozilla/5.0"})
    b = BeautifulSoup(r["html"], "lxml")
    data = {"date": [], "open": [], "close": [], "high": [], "low": []}
    for i, td in enumerate(b.findAll("td")):
        if i % 6 == 0:
            s = td.find("span").string.split(",")[1:]
            s = ",".join(s)
            data["date"].append(dt.datetime.strptime(s, " %B %d, %Y"))
        elif i % 6 == 1:
            data["open"].append(_float(td.string))
        elif i % 6 == 2:
            data["high"].append(_float(td.string))
        elif i % 6 == 3:
            data["low"].append(_float(td.string))
        elif i % 6 == 4:
            data["close"].append(_float(td.string))
    df = pd.DataFrame(data)
    df = df.iloc[::-1]
    return df


def get_historical_fromyh(code, start=None, end=None):
    """
    雅虎财经数据源，支持数据丰富，不限于美股。但存在部分历史数据确实 NAN 或者周末进入交易日的现象，可能数据需要进一步清洗和处理。

    :param code:
    :param start:
    :param end:
    :return:
    """
    if code.startswith("YH-"):
        code = code[3:]
    start_obj = dt.datetime.strptime(start, "%Y%m%d")
    today_obj = dt.datetime.now()
    fromnow = (today_obj - start_obj).days
    if fromnow < 20:
        range_ = "1mo"
    elif fromnow < 50:
        range_ = "3mo"
    elif fromnow < 150:
        range_ = "6mo"
    elif fromnow < 300:
        range_ = "1y"
    elif fromnow < 600:
        range_ = "2y"
    elif fromnow < 1500:
        range_ = "5y"
    else:
        range_ = "10y"
    url = "https://query1.finance.yahoo.com/v8\
/finance/chart/{code}?region=US&lang=en-US&includePrePost=false\
&interval=1d&range={range_}&corsDomain=finance.yahoo.com&.tsrc=finance".format(
        code=code, range_=range_
    )
    # 该 API 似乎也支持起止时间选择参数，period1=1427500800&period2=1585353600
    # 也可直接从历史数据页面爬取： https://finance.yahoo.com/quote/CSGOLD.SW/history?period1=1427500800&period2=1585353600&interval=1d&filter=history&frequency=1d
    r = rget_json(url)
    data = {}
    datel = []
    for t in r["chart"]["result"][0]["timestamp"]:
        t = dt.datetime.fromtimestamp(t)
        if t.second != 0:
            t -= dt.timedelta(hours=8)
        datel.append(t.replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0))

    data["date"] = datel
    for k in ["close", "open", "high", "low"]:
        data[k] = r["chart"]["result"][0]["indicators"]["quote"][0][k]
    df = pd.DataFrame(data)
    return df


@data_source("jq")
def get_macro(table, start, end, datecol="stat_year"):
    df = macro.run_query(
        query(getattr(macro, table))
        .filter(getattr(getattr(macro, table), datecol) >= start)
        .filter(getattr(getattr(macro, table), datecol) <= end)
        .order_by(getattr(getattr(macro, table), datecol))
    )
    df[datecol] = pd.to_datetime(df[datecol])
    df["date"] = df[datecol]
    return df


def set_handler(method="daily", f=None):
    """
    为 ``get_daily``, ``get_bar`` 或 ``get_rt`` 设置 hook，优先按照函数 f 进行处理，若返回 None，再按一般情形处理

    :param method: str. daily, rt, bar
    :param f: func, default None.
    :return: None
    """
    setattr(thismodule, "get_" + method + "_handler", f)


def _get_daily(
    code, start=None, end=None, prev=365, _from=None, wrapper=True, handler=True, **kws
):
    """
    universal fetcher for daily historical data of literally everything has a value in market.
    数据来源包括天天基金，雪球，英为财情，外汇局官网，聚宽，标普官网，bloomberg，雅虎财经等。

    :param code: str.

            1. 对于沪深市场的股票，指数，ETF，LOF 场内基金，可转债和债券，直接使用其代码，主要开头需要包括 SH 或者 SZ。

            2. 对于香港市场的股票，指数，使用其数字代码，同时开头要添加 HK。

            3. 对于美国市场的股票，指数，ETF 等，直接使用其字母缩写代码即可。

            4. 对于人民币中间价数据，使用 "USD/CNY" 的形式，具体可能的值可在 http://www.chinamoney.com.cn/chinese/bkccpr/ 历史数据的横栏查询

            5. 对于所有可以在 cn.investing.com 网站查到的金融产品，其代码可以是该网站对应的统一代码，或者是网址部分，比如 DAX 30 的概览页面为 https://cn.investing.com/indices/germany-30，那么对应代码即为 "indices/germany-30"。也可去网页 inspect 手动查找其内部代码（一般不需要自己做，推荐直接使用网页url作为 code 变量值），手动 inspect 加粗的实时价格，其对应的网页 span class 中的 pid 的数值即为内部代码。

            6. 对于国内发行的基金，使用基金代码，同时开头添加 F。

            7. 对于国内发行的货币基金，使用基金代码，同时开头添加 M。（全部按照净值数据处理）

            8. 形如 peb-000807.XSHG 或 peb-SH000807 格式的数据，可以返回每周的指数估值情况，需要 enable 聚宽数据源方可查看。

            9. 形如 iw-000807.XSHG 或 iw-SH000807 格式的数据，可以返回每月的指数成分股和实时权重，需要 enable 聚宽数据源方可查看。

            10. 形如 fs-SH501018 格式的数据，可以返回指定场内基金每日份额，需要 enable 聚宽数据源方可查看。

            11. 形如 SP5475707.2 格式的数据，可以返回标普官网相关指数的日线数据（最近十年），id 5475707 部分可以从相关指数 export 按钮获取的链接中得到，小数点后的部分代表保存的列数。参考链接：https://us.spindices.com/indices/equity/sp-global-oil-index

            12. 形如 BB-FGERBIU:ID 格式的数据，对应网页 https://www.bloomberg.com/quote/FGERBIU:ID，可以返回彭博的数据（最近五年）

            13. 形如 sw-801720 格式的数据，可以返回对应申万行业的历史数据情况，需要 enable 聚宽数据源方可查看。

            14. 形如 teb-SH000300 格式的数据，返回每周指数盈利和净资产总值数据(单位：亿人民币元)，需要 enbale 聚宽数据方可查看。

            15. 形如 YH-CSGOLD.SW 格式的数据，返回雅虎财经标的日线数据（最近十年）。代码来自标的网页 url：https://finance.yahoo.com/quote/CSGOLD.SW。

            16. 形如 FT-22065529 格式的数据或 FT-INX:IOM，可以返回 financial times 的数据，推荐直接用后者。前者数字代码来源，打开浏览器 network 监视，切换图标时间轴时，会新增到 https://markets.ft.com/data/chartapi/series 的 XHR 请求，其 request payload 里的 [elements][symbol] 即为该指数对应数字。

            17. 形如 FTC-WTI+Crude+Oil 格式的数据，开头可以是 FTC, FTE, FTX, FTF, FTB, FTI 对应 commdities，equities，currencies，funds，bonds，indicies。其中 FTI 和 FT 相同。

            18. 形如 mcy-MAC_AREA_UNEMPLOY 格式的数据，返回相应的宏观数据，需要聚宽数据源。mcy，mcq，mcm 代表年度，季度和月度的数据，code 为表名，可以参考 https://www.joinquant.com/help/api/help?name=macroData

    :param start: str. "20200101", "2020/01/01", "2020-01-01" are all legal. The starting date of daily data.
    :param end: str. format is the same as start. The ending date of daily data.
    :param prev: Optional[int], default 365. If start is not specified, start = end-prev.
    :param _from: Optional[str]. 一般用户不需设定该选项。can be one of "xueqiu", "zjj", "investing", "tiantianjijin". Only used for debug to
        enfore data source. For common use, _from can be chosed automatically based on code in the run time.
    :param wrapper: bool. 一般用户不需设定该选项。
    :param handler: bool. Default True. 若为 False，则 handler 钩子失效，用于钩子函数中的嵌套。
    :return: pd.Dataframe.
        must include cols: date[pd.Timestamp]，close[float64]。
    """
    if handler:
        if getattr(thismodule, "get_daily_handler", None):
            args = inspect.getargvalues(inspect.currentframe())
            f = getattr(thismodule, "get_daily_handler")
            fr = f(**args.locals)
            if fr:
                return fr

    if not end:
        end_obj = today_obj()
    else:
        end_obj = dstr2dobj(end)
    if not start:
        start_obj = end_obj - dt.timedelta(days=prev)
    else:
        start_obj = dstr2dobj(start)

    if not _from:
        if code.startswith("SH") or code.startswith("SZ"):
            _from = "xueqiu"
        elif code.endswith("/CNY") or code.startswith("CNY/"):
            _from = "zjj"
        elif code.isdigit():
            _from = "cninvesting"
        elif code[0] in ["F", "M"] and code[1:].isdigit():
            _from = "ttjj"
        elif code.startswith("HK") and code[2:].isdigit() and len(code) == 7:
            _from = "xueqiu"
            code = code[2:]
        elif code.startswith("SP") and code[2:].split(".")[0].isdigit():
            _from = "SP"
        elif len(code.split("-")) >= 2 and len(code.split("-")[0]) <= 3:
            # peb-000807.XSHG
            _from = code.split("-")[0]
            code = "-".join(code.split("-")[1:])
        elif len(code[1:].split("/")) == 2:
            _from = "cninvesting"
            code = get_investing_id(code)
        else:
            _from = "xueqiu"

    count = (today_obj() - start_obj).days + 1
    start_str = start_obj.strftime("%Y/%m/%d")
    end_str = end_obj.strftime("%Y/%m/%d")
    if _from in ["cninvesting", "investing", "default", "IN"]:
        df = get_historical_fromcninvesting(code, start_str, end_str)
        df = prettify(df)
    elif _from in ["xueqiu", "xq", "snowball", "XQ"]:
        df = get_historical_fromxq(code, count)
        df = prettify(df)
    elif _from in ["zhongjianjia", "zjj", "chinamoney", "ZJJ"]:
        df = get_rmb(start, end, prev, currency=code)
    elif _from in ["ttjj", "tiantianjijin", "xalpha", "eastmoney"]:
        df = get_fund(code)

    elif _from == "peb":
        df = _get_peb_range(code=code, start=start_str, end=end_str)

    elif _from == "iw":
        df = _get_index_weight_range(code=code, start=start_str, end=end_str)

    elif _from == "fs":
        df = get_fundshare_byjq(code, start=start, end=end)

    elif _from == "SP":
        df = get_historical_fromsp(code, start=start, end=end)

    elif _from == "BB":
        df = get_historical_frombb(code, start=start, end=end)

    elif _from == "sw":
        df = get_sw_from_jq(code, start=start, end=end)

    elif _from == "teb":
        df = get_teb_range(code, start=start, end=end)

    elif _from == "YH":
        df = get_historical_fromyh(code, start=start, end=end)

    elif _from in ["FT", "FTI"]:
        df = get_historical_fromft(code, start=start, end=end)

    elif _from == "FTE":
        df = get_historical_fromft(code, start=start, end=end, _type="equities")

    elif _from == "FTB":
        df = get_historical_fromft(code, start=start, end=end, _type="bonds")

    elif _from == "FTF":
        df = get_historical_fromft(code, start=start, end=end, _type="funds")

    elif _from == "FTX":
        df = get_historical_fromft(code, start=start, end=end, _type="currencies")

    elif _from == "FTC":
        df = get_historical_fromft(code, start=start, end=end, _type="commodities")

    elif _from == "INA":  # investing app
        code = get_investing_id(code, app=True)
        df = get_historical_fromcninvesting(code, start_str, end_str, app=True)
        df = prettify(df)

    elif _from == "mcy":
        df = get_macro(code, start=start[:4], end=end[:4], datecol="stat_year")

    elif _from == "mcq":
        df = get_macro(code, start=start, end=end, datecol="stat_quarter")

    elif _from == "mcm":
        df = get_macro(code, start=start, end=end, datecol="stat_month")

    elif _from == "mcd":
        df = get_macro(code, start=start, end=end, datecol="day")

    else:
        raise ParserFailure("no such data source: %s" % _from)

    if wrapper or len(df) == 0:
        return df
    else:
        df = df[df.date <= end_str]
        df = df[df.date >= start_str]
        return df


def _float(n):
    try:
        n = n.replace(",", "")
    except AttributeError:
        pass
    return float(n)


def get_xueqiu_rt(code, token="a664afb60c7036c7947578ac1a5860c4cfb6b3b5"):
    if code.startswith("HK"):
        code = code[2:]
    url = "https://stock.xueqiu.com/v5/stock/quote.json?symbol={code}&extend=detail"
    r = rget_json(
        url.format(code=code),
        cookies={"xq_a_token": token},
        headers={"user-agent": "Mozilla/5.0"},
    )
    n = r["data"]["quote"]["name"]
    q = r["data"]["quote"]["current"]
    try:
        q = _float(q)
    except TypeError:  # 针对雪球实时在9点后开盘前可能出现其他情形的fixup， 效果待 check
        # 现在的怀疑是在9am 到9:15 am, 雪球 API current 字段返回 Null
        q = _float(r["data"]["quote"]["last_close"])
    q_ext = r["data"]["quote"].get("current_ext", None)
    percent = r["data"]["quote"]["percent"]
    try:
        percent = _float(percent)
    except:
        pass
    currency = r["data"]["quote"]["currency"]
    market = r["data"]["market"]["region"]
    return {
        "name": n,
        "current": q,
        "percent": percent,
        "current_ext": _float(q_ext) if q_ext else None,
        "currency": currency,
        "market": market,  # HK, US, CN
    }


def get_cninvesting_rt(suburl, app=False):
    if not app:
        url = "https://cn.investing.com"
    else:
        url = "https://cnappapi.investing.com"
    if not suburl.startswith("/"):
        url += "/"
    url += suburl
    if not app:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36"
        }
    else:
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Accept-Language": "zh-cn",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "User-Agent": "Investing.China/0.0.3 CFNetwork/1121.2.2 Darwin/19.3.0",
            "ccode": "CN",
            #'ccode_time': '1585551041.986028',
            "x-app-ver": "117",
            "x-meta-ver": "14",
            "x-os": "ios",
            "x-uuid": str(uuid4()),
            "Host": "cn.investing.com",
            "X-Requested-With": "XMLHttpRequest",
        }

    r = rget(url, headers=headers,)
    s = BeautifulSoup(r.text, "lxml")
    last_last = s.find("span", id="last_last")
    q = _float(last_last.string)
    name = s.find("h1").string.strip()
    ind = 0
    l = s.find("div", class_="lighterGrayFont").contents
    for i, c in enumerate(l):
        if isinstance(c, str) and c.strip() == "货币":
            ind = i
            break
    if ind == 0:
        currency = None
    else:
        currency = l[ind - 1].string
    percent = _float(
        s.find("span", attrs={"dir": "ltr", "class": "parentheses"}).string[:-1]
    )
    panhou = s.find("div", class_="afterHoursInfo")
    if panhou:
        q_ext = _float(panhou.find("span").string)
    else:
        q_ext = None
    market = None
    for span in s.findAll("span", class_="elp"):
        if span.find("a") and span.find("a")["href"].startswith("/markets"):
            market = span.string
    market = region_trans.get(market, market)
    return {
        "name": name,
        "current": q,
        "current_ext": q_ext,
        "currency": currency,
        "percent": percent,
        "market": market,
    }


def get_rt_from_sina(code):
    if (
        code.startswith("SH") or code.startswith("SZ") or code.startswith("HK")
    ) and code[2:].isdigit():
        tinycode = code[:2].lower() + code[2:]
        if code.startswith("HK"):  # 港股额外要求实时
            tinycode = "rt_" + tinycode
    else:  # 美股
        tinycode = "gb_"
        if code.startswith("."):
            code = code[1:]
        tinycode += code.lower()
    r = rget("https://hq.sinajs.cn/list={tinycode}".format(tinycode=tinycode))
    l = r.text.split("=")[1].split(",")
    d = {}
    d["name"] = l[0].strip('"')
    if (
        code.startswith("SH") or code.startswith("SZ") or code.startswith("HK")
    ) and code[2:].isdigit():
        if code.startswith("HK"):
            d["current"] = float(l[9])  # 英文股票名称占位
            d["currency"] = "HKD"
            d["percent"] = round(float(l[8]), 2)
            d["market"] = "HK"
        else:
            d["current"] = float(l[3])
            d["currency"] = "CNY"
            d["percent"] = round((float(l[3]) / float(l[2]) - 1) * 100, 2)
            d["market"] = "CN"
        d["current_ext"] = None

    else:
        d["currency"] = "USD"
        d["current"] = float(l[1])
        d["percent"] = float(l[2])
        d["current_ext"] = None
        d["market"] = "US"
    return d


def make_ft_url(code, _type="indices"):
    """

    :param code:
    :param _type: indices, commodities, currencies, funds, equities, bonds
    :return:
    """
    if _type == "indices":
        url = "https://markets.ft.com/data/indices/tearsheet/summary?s={code}".format(
            code=code
        )
    elif _type == "commodities":
        url = "https://markets.ft.com/data/commodities/tearsheet/summary?c={code}".format(
            code=code
        )
    elif _type == "currencies":
        url = "https://markets.ft.com/data/currencies/tearsheet/summary?s={code}".format(
            code=code
        )
    elif _type == "funds":
        url = "https://markets.ft.com/data/funds/tearsheet/summary?s={code}".format(
            code=code
        )
    elif _type == "equities":
        url = "https://markets.ft.com/data/equities/tearsheet/summary?s={code}".format(
            code=code
        )
    elif _type == "bonds":
        url = "https://markets.ft.com/data/bonds/tearsheet/summary?s={code}".format(
            code=code
        )
    else:
        raise ParserFailure("no reconginzed type for ft datasource: %s" % _type)
    return url


@lru_cache(maxsize=1024)
def get_ft_id(code, _type="indices"):
    url = make_ft_url(code, _type=_type)
    r = rget(url)
    b = BeautifulSoup(r.text, "lxml")
    return eval(
        b.find("section", class_="mod-tearsheet-add-to-watchlist")["data-mod-config"]
    )["xid"]


def get_rt_from_ft(code, _type="indices"):
    url = make_ft_url(code, _type=_type)
    r = rget(url)
    b = BeautifulSoup(r.text, "lxml")
    d = {}
    d["name"] = b.find("h1").string
    d["current"] = _float(b.find("span", class_="mod-ui-data-list__value").string)
    d["percent"] = _float(
        b.findAll("span", class_="mod-ui-data-list__value")[1]
        .find("span")
        .contents[1]
        .split("/")[1][:-1]
    )
    d["current_ext"] = None
    d["market"] = None
    d["currency"] = b.find("span", class_="mod-ui-data-list__label").string.split("(")[
        1
    ][:-1]
    return d


@lru_cache_time(ttl=300, maxsize=512)
def get_newest_netvalue(code):
    """
    防止天天基金总量 API 最新净值更新不及时，获取基金最新公布净值及对应日期

    :param code: six digits string for fund.
    :return: netvalue, %Y-%m-%d
    """
    code = code[1:]
    r = rget("http://fund.eastmoney.com/{code}.html".format(code=code))
    s = BeautifulSoup(r.text, "lxml")
    return (
        float(
            s.findAll("dd", class_="dataNums")[1]
            .find("span", class_="ui-font-large")
            .string
        ),
        str(s.findAll("dt")[1]).split("(")[1].split(")")[0][7:],
    )


def get_rt(
    code, _from=None, double_check=False, double_check_threhold=0.005, handler=True
):
    """
    universal fetcher for realtime price of literally everything.

    :param code: str. 规则同 :func:`get_daily`. 需要注意场外基金和外汇中间价是不支持实时行情的，因为其每日只有一个报价。对于 investing 的数据源，只支持网址格式代码。
    :param _from: Optional[str]. can be one of "xueqiu", "investing". Only used for debug to
        enfore data source. For common use, _from can be chosed automatically based on code in the run time.
    :param double_check: Optional[bool], default False. 如果设为 True，只适用于 A 股，美股，港股实时行情，会通过至少两个不同的数据源交叉验证，确保正确。
            适用于需要自动交易等情形，防止实时数据异常。
    :param handler: bool. Default True. 若为 False，则 handler 钩子失效，用于钩子函数中的嵌套。
    :return: Dict[str, Any].
        包括 "name", "current", "percent" 三个必有项和 "current_ext"（盘后价格）, "currency" （计价货币）， "market" (发行市场)可能为 ``None`` 的选项。
    """
    # 对于一些标的，get_rt 的主任务可能不是 current 价格，而是去拿 market currency 这些元数据
    # 现在用的新浪实时数据源延迟严重， double check 并不靠谱，港股数据似乎有15分钟延迟（已解决）
    # 雪球实时和新浪实时在9：00之后一段时间可能都有问题
    # FT 数据源有10到20分钟的延迟
    if handler:
        if getattr(thismodule, "get_rt_handler", None):
            args = inspect.getargvalues(inspect.currentframe())
            f = getattr(thismodule, "get_rt_handler")
            fr = f(**args.locals)
            if fr:
                return fr

    if not _from:
        # if code.startswith("HK") and code[2:].isdigit():
        #     _from = "xueqiu"
        if len(code.split("-")) >= 2 and len(code.split("-")[0]) <= 3:
            _from = code.split("-")[0]
            code = "-".join(code.split("-")[1:])
        elif len(code.split("/")) > 1:
            _from = "investing"
        else:  # 默认不启用新浪实时，只做双重验证备份
            _from = "xueqiu"
    if _from in ["cninvesting", "investing"]:
        try:
            return get_cninvesting_rt(code)
        except Exception as e:
            logger.warning(
                "Fails due to %s, now trying app source of investing.com" % e.args[0]
            )
            return get_cninvesting_rt(code, app=True)
    elif double_check and _from in ["xueqiu", "sina"]:
        r1 = get_xueqiu_rt(code, token=get_token())
        r2 = get_rt_from_sina(code)
        if abs(r1["current"] / r2["current"] - 1) > double_check_threhold:
            raise DataPossiblyWrong("realtime data unmatch for %s" % code)
        return r1
    elif _from in ["xueqiu", "xq", "snowball"]:
        try:
            return get_xueqiu_rt(code, token=get_token())
        except Exception as e:  # 默认雪球实时引入备份机制
            logging.warning(
                "Fails due to %s, now trying backup data source from sina" % e.args[0]
            )
            return get_rt_from_sina(code)
    elif _from in ["sina", "sn", "xinlang"]:
        return get_rt_from_sina(code)
    elif _from in ["FT", "ft"]:
        return get_rt_from_ft(code)
    elif _from == "FTE":
        return get_rt_from_ft(code, _type="equities")
    elif _from == "FTB":
        return get_rt_from_ft(code, _type="bonds")
    elif _from == "FTF":
        return get_rt_from_ft(code, _type="funds")
    elif _from == "FTX":
        return get_rt_from_ft(code, _type="currencies")
    elif _from == "FTC":
        return get_rt_from_ft(code, _type="commodities")
    elif _from in ["INA"]:  # investing app
        return get_cninvesting_rt(code, app=True)
    else:
        raise ParserFailure("unrecoginzed _from for %s" % _from)


get_realtime = get_rt
get_now = get_rt

_cached_data = {}


def reset_cache():
    """
    clear all cache of daily data in memory.

    :return: None.
    """
    global _cached_data
    _cached_data = {}
    setattr(thismodule, "cached_dict", {})


def cached(s):
    """
    **Deprecated**, use :func:`cachedio` instead, where ``backend="memory"``.

    Usage as follows:

    .. code-block:: python

       @cached("20170101")
       def get_daily(*args, **kws):
          return xa.get_daily(*args, **kws)

    Automatically cache the result in memory and avoid refetching
    :param s: str. eg. "20160101", the starting date of cached table.
    :return: wrapped function.
    """

    def cached_start(f):
        @wraps(f)
        def wrapper(*args, **kws):
            print("cached function is deprecated, please instead use cachedio")
            if args:
                code = args[0]
            else:
                code = kws.get("code")
            start = kws.get("start", None)
            end = kws.get("end", None)
            prev = kws.get("prev", None)
            if not prev:
                prev = 365
            if not end:
                end_obj = today_obj()
            else:
                end_obj = dstr2dobj(end)
            if not start:
                start_obj = end_obj - dt.timedelta(prev)
            else:
                start_obj = dstr2dobj(start)
            start_str = start_obj.strftime("%Y%m%d")
            end_str = end_obj.strftime("%Y%m%d")
            kws["start"] = s
            kws["end"] = dt.datetime.now().strftime("%Y%m%d")
            global _cached_data
            _cached_data.setdefault(s, {})
            if code not in _cached_data[s]:
                df = f(*args, **kws)
                # print("cached %s" % code)
                _cached_data[s][code] = df
            else:
                pass
                # print("directly call cache")
            df = _cached_data[s][code]
            df = df[df["date"] <= end_str]
            df = df[df["date"] >= start_str]

            return df

        return wrapper

    return cached_start


def cachedio(**ioconf):
    """
    用法类似:func:`cached`，通用透明缓存器，用来作为 (code, start, end ...) -> pd.DataFrame 形式函数的缓存层，
    避免重复爬取已有数据。

    :param **ioconf: 可选关键字参数 backend: csv or sql or memory,
        path: csv 文件夹或 sql engine， refresh True 会刷新结果，重新爬取, default False，
        prefix 是 key 前统一部分, 缓存 hash 标志
    :return:
    """

    def cached(f):
        @wraps(f)
        def wrapper(*args, **kws):
            if args:
                code = args[0]
            else:
                code = kws.get("code")
            date = ioconf.get("date", "date")
            precached = ioconf.get("precached", None)
            key = kws.get("key", code)
            key = key.replace("/", " ")
            start = kws.get("start", None)
            end = kws.get("end", None)
            prev = kws.get("prev", None)
            prefix = ioconf.get("prefix", "")
            key = prefix + key
            # print("xdebug: %s" % ioconf.get("backend", "no"))
            if precached:
                precached = precached.replace("/", "").replace("-", "")
                precached_obj = dt.datetime.strptime(precached, "%Y%m%d")
            if not prev:
                prev = 365
            if not end:
                end_obj = today_obj()
            else:
                end_obj = dt.datetime.strptime(
                    end.replace("/", "").replace("-", ""), "%Y%m%d"
                )

            if not start:
                start_obj = end_obj - dt.timedelta(days=prev)
            else:
                start_obj = dt.datetime.strptime(
                    start.replace("/", "").replace("-", ""), "%Y%m%d"
                )

            start_str = start_obj.strftime("%Y%m%d")
            end_str = end_obj.strftime("%Y%m%d")
            backend = ioconf.get("backend")
            refresh = ioconf.get("refresh", False)
            path = ioconf.get("path")
            kws["start"] = start_str
            kws["end"] = end_str
            if not backend:
                df = f(*args, **kws)
                df = df[df["date"] <= kws["end"]]
                df = df[df["date"] >= kws["start"]]
                return df
            else:
                if backend == "csv":
                    key = key + ".csv"
                if not getattr(thismodule, "cached_dict", None):
                    setattr(thismodule, "cached_dict", {})
                if refresh:
                    is_changed = True
                    df0 = f(*args, **kws)

                else:  # non refresh
                    try:
                        if backend == "csv":
                            if key in getattr(thismodule, "cached_dict"):
                                # 即使硬盘级别的缓存，也有内存层，加快读写速度
                                df0 = getattr(thismodule, "cached_dict")[key]
                            else:
                                df0 = pd.read_csv(os.path.join(path, key))
                        elif backend == "sql":
                            if key in getattr(thismodule, "cached_dict"):
                                df0 = getattr(thismodule, "cached_dict")[key]
                            else:
                                df0 = pd.read_sql(key, path)
                        elif backend == "memory":
                            df0 = getattr(thismodule, "cached_dict")[key]
                        else:
                            raise ValueError("no %s option for backend" % backend)
                        df0[date] = pd.to_datetime(df0[date])
                        # 向前延拓
                        is_changed = False
                        if df0.iloc[0][date] > start_obj:
                            kws["start"] = start_str
                            kws["end"] = (
                                df0.iloc[0][date] - pd.Timedelta(days=1)
                            ).strftime("%Y%m%d")
                            if has_weekday(kws["start"], kws["end"]):
                                # 考虑到海外市场的不同情况，不用 opendate 判断，采取保守型判别
                                df1 = f(*args, **kws)
                                if len(df1) > 0:
                                    df1 = df1[df1["date"] <= kws["end"]]
                                if len(df1) > 0:
                                    is_changed = True
                                    df0 = df1.append(df0, ignore_index=True)
                        # 向后延拓
                        if df0.iloc[-1][date] < end_obj:
                            nextday_str = (
                                df0.iloc[-1][date] + dt.timedelta(days=1)
                            ).strftime("%Y%m%d")
                            if len(df0[df0["date"] == df0.iloc[-1]["date"]]) == 1:
                                kws["start"] = (df0.iloc[-1][date]).strftime("%Y%m%d")
                            else:  # 单日多行的表默认最后一日是准确的，不再刷新了
                                kws["start"] = nextday_str
                            kws["end"] = end_str
                            if has_weekday(nextday_str, kws["end"]):  # 新更新的日期里有工作日
                                df2 = f(*args, **kws)
                                if len(df2) > 0:
                                    df2 = df2[df2["date"] >= kws["start"]]
                                if len(df2) > 0:
                                    is_changed = True
                                    if (
                                        len(df0[df0["date"] == df0.iloc[-1]["date"]])
                                        == 1
                                    ):
                                        df0 = df0.iloc[:-1]
                                    df0 = df0.append(df2, ignore_index=True)
                            # 注意这里抹去更新了原有最后一天的缓存，这是因为日线最新一天可能有实时数据污染

                    except (FileNotFoundError, exc.ProgrammingError, KeyError):
                        if precached:
                            if start_obj > precached_obj:
                                kws["start"] = precached
                            if end_obj < today_obj():
                                kws["end"] = (
                                    today_obj() - dt.timedelta(days=1)
                                ).strftime("%Y%m%d")
                        is_changed = True
                        df0 = f(*args, **kws)

                if df0 is not None and len(df0) > 0 and is_changed:
                    if backend == "csv":
                        df0.to_csv(os.path.join(path, key), index=False)
                    elif backend == "sql":
                        df0.to_sql(key, con=path, if_exists="replace", index=False)
                    # elif backend == "memory":
                    # 总是刷新内存层，即使是硬盘缓存
                    d = getattr(thismodule, "cached_dict")
                    d[key] = df0

            if df0 is not None and len(df0) > 0:
                df0 = df0[df0["date"] <= end_str]
                df0 = df0[df0["date"] >= start_str]

            return df0

        return wrapper

    return cached


def fetch_backend(key):
    prefix = ioconf.get("prefix", "")
    key = prefix + key
    backend = ioconf.get("backend")
    path = ioconf.get("path")
    if backend == "csv":
        key = key + ".csv"

    try:
        if backend == "csv":
            df0 = pd.read_csv(os.path.join(path, key))
        elif backend == "sql":
            df0 = pd.read_sql(key, path)
        else:
            raise ValueError("no %s option for backend" % backend)

        return df0

    except (FileNotFoundError, exc.ProgrammingError, KeyError):
        return None


def save_backend(key, df, mode="a"):
    prefix = ioconf.get("prefix", "")
    key = prefix + key
    backend = ioconf.get("backend")
    path = ioconf.get("path")
    if backend == "csv":
        key = key + ".csv"

    if backend == "csv":
        df.to_csv(os.path.join(path, key), index=False, mode=mode)
    elif backend == "sql":
        if mode == "a":
            mode = "append"
        else:
            mode = "replace"
        df.to_sql(key, con=path, if_exists=mode, index=False)
    else:
        raise ValueError("no %s option for backend" % backend)

    logger.debug("%s saved into backend successfully" % key)


def check_cache(*args, **kws):
    assert (
        _get_daily(*args, wrapper=False, **kws)
        .reset_index(drop=True)
        .equals(get_daily(*args, **kws).reset_index(drop=True))
    )


@data_source("jq")
def _get_index_weight_range(code, start, end):
    if len(code.split(".")) != 2:
        code = _inverse_convert_code(code)
    start_obj = dt.datetime.strptime(start.replace("-", "").replace("/", ""), "%Y%m%d")
    end_obj = dt.datetime.strptime(end.replace("-", "").replace("/", ""), "%Y%m%d")
    start_m = start_obj.replace(day=1)
    if start_m < start_obj:
        start_m = start_m + relativedelta(months=1)
    end_m = end_obj.replace(day=1)
    if end_obj < end_m:
        end_m = end_m - relativedelta(months=1)
    d = start_m

    df = pd.DataFrame({"code": [], "weight": [], "display_name": [], "date": []})
    while True:
        if d > end_m:

            df["date"] = pd.to_datetime(df["date"])
            return df
        logger.debug("fetch index weight on %s for %s" % (d, code))
        df0 = get_index_weights(index_id=code, date=d.strftime("%Y-%m-%d"))
        df0["code"] = df0.index
        df = df.append(df0, ignore_index=True)
        d = d + relativedelta(months=1)


@data_source("jq")
def _get_peb_range(code, start, end):  # 盈利，净资产，总市值
    """
    获取指定指数一段时间内的 pe pb 值。

    :param code: 聚宽形式指数代码。
    :param start:
    :param end:
    :return: pd.DataFrame
    """
    if len(code.split(".")) != 2:
        code = _inverse_convert_code(code)
    data = {"date": [], "pe": [], "pb": []}
    for d in pd.date_range(start=start, end=end, freq="W-FRI"):
        data["date"].append(d)
        logger.debug("compute pe pb on %s" % d)
        r = get_peb(code, date=d.strftime("%Y-%m-%d"))
        data["pe"].append(r["pe"])
        data["pb"].append(r["pb"])
    return pd.DataFrame(data)


def set_backend(**ioconf):
    """
    设定 xalpha get_daily 函数的缓存后端，默认为内存。 ioconf 参数设置可参考 :func:`cachedio`

    :param ioconf:
    :return: None.
    """

    if not ioconf:
        ioconf = {"backend": "memory"}
    get_daily = cachedio(**ioconf)(_get_daily)
    prefix = ioconf.get("prefix", "")
    ioconf["prefix"] = "iw-" + prefix
    get_index_weight_range = cachedio(**ioconf)(_get_index_weight_range)
    ioconf["prefix"] = "peb-" + prefix
    get_peb_range = cachedio(**ioconf)(_get_peb_range)
    setattr(thismodule, "get_daily", get_daily)
    setattr(xamodule, "get_daily", get_daily)
    setattr(thismodule, "get_index_weight_range", get_index_weight_range)
    setattr(thismodule, "get_peb_range", get_peb_range)
    ioconf["prefix"] = prefix
    setattr(thismodule, "ioconf", ioconf)


set_backend()


@data_source("jq")
def get_peb(index, date=None, table=False):
    """
    获取指数在指定日期的 pe 和 pb。采用当时各公司的最新财报和当时的指数成分股权重加权计算。

    :param index: str. 聚宽形式的指数代码。
    :param date: str. %Y-%m-%d
    :param table: Optioanl[bool], default False. True 时返回整个计算的 DataFrame，用于 debug。
    :return: Dict[str, float]. 包含 pe 和 pb 值的字典。
    """
    if len(index.split(".")) == 2:
        index = _convert_code(index)
    middle = dt.datetime.strptime(
        date.replace("/", "").replace("-", ""), "%Y%m%d"
    ).replace(day=1)
    iwdf = get_index_weight_range(
        index,
        start=(middle - dt.timedelta(days=5)).strftime("%Y-%m-%d"),
        end=(middle + dt.timedelta(days=5)).strftime("%Y-%m-%d"),
    )
    q = query(valuation).filter(valuation.code.in_(list(iwdf.code)))
    logger.debug("get_fundamentals on %s" % (date))
    df = get_fundamentals(q, date=date)
    df = df.merge(iwdf, on="code")
    df["e"] = df["weight"] / df["pe_ratio"]
    df["b"] = df["weight"] / df["pb_ratio"]
    df["p"] = df["weight"]
    tote = df.e.sum()
    totb = df.b.sum()
    if table:
        return df
    return {"pe": round(100.0 / tote, 3), "pb": round(100.0 / totb, 3)}


@data_source("jq")
def get_sw_from_jq(code, start=None, end=None, **kws):
    """

    :param code: str. eg. 801180 申万行业指数
    :param start:
    :param end:
    :param kws:
    :return:
    """
    df = finance.run_query(
        query(finance.SW1_DAILY_VALUATION)
        .filter(finance.SW1_DAILY_VALUATION.date >= start)
        .filter(finance.SW1_DAILY_VALUATION.date <= end)
        .filter(finance.SW1_DAILY_VALUATION.code == code)
        .order_by(finance.SW1_DAILY_VALUATION.date.asc())
    )
    df["date"] = pd.to_datetime(df["date"])
    return df


def get_teb(code, date):
    if len(code.split(".")) != 2:
        code = _inverse_convert_code(code)
    sl = get_index_stocks(code, date=date)
    df = get_fundamentals(query(valuation).filter(valuation.code.in_(sl)), date=date)
    df["e"] = df["market_cap"] / df["pe_ratio"]
    df["b"] = df["market_cap"] / df["pb_ratio"]
    return {"e": df["e"].sum(), "b": df["b"].sum()}  # 亿人民币


def get_teb_range(code, start, end):
    if len(code.split(".")) != 2:
        code = _inverse_convert_code(code)
    data = {"date": [], "e": [], "b": []}
    for d in pd.date_range(start, end, freq="W-FRI"):
        data["date"].append(d)
        r = get_teb(code, d.strftime("%Y-%m-%d"))
        data["e"].append(r["e"])
        data["b"].append(r["b"])
    df = pd.DataFrame(data)
    return df


def _convert_code(code):
    """
    将聚宽形式的代码转化为 xalpha 形式

    :param code:
    :return:
    """
    no, mk = code.split(".")
    if mk == "XSHG":
        return "SH" + no
    elif mk == "XSHE":
        return "SZ" + no


def _inverse_convert_code(code):
    """
    将 xalpha 形式的代码转化为聚宽形式

    :param code:
    :return:
    """

    if code.startswith("SH"):
        return code[2:] + ".XSHG"
    elif code.startswith("SZ"):
        return code[2:] + ".XSHE"


@lru_cache_time(ttl=60, maxsize=512)
def get_bar(code, prev=24, interval=3600, _from=None, handler=True):
    """

    :param code: str. 支持雪球和英为的代码
    :param prev: points of data from now to back, often limited by API around several hundreds
    :param interval: float, seconds. need to match the corresponding API,
        typical values include 60, 300, 3600, 86400, 86400*7
    :param handler: bool. Default True. 若为 False，则 handler 钩子失效，用于钩子函数中的嵌套。
    :return: pd.DataFrame
    """
    if handler:
        if getattr(thismodule, "get_bar_handler", None):
            args = inspect.getargvalues(inspect.currentframe())
            f = getattr(thismodule, "get_bar_handler")
            fr = f(**args.locals)
            if fr:
                return fr

    if not _from:
        if code.startswith("SH") or code.startswith("SZ"):
            _from = "xueqiu"
        elif code.isdigit():
            _from = "cninvesting"
        elif code.startswith("HK") and code[2:].isdigit() and len(code) == 7:
            _from = "xueqiu"
            code = code[2:]
        elif len(code.split("-")) > 2 and len(code.split("-")[0]) <= 3:
            _from = code.split("-")[0]
            code = "-".join(code.split("-")[1:])
        elif len(code.split("/")) > 1:
            _from = "cninvesting"
            code = get_investing_id(code)
        else:
            _from = "xueqiu"  # 美股
    if _from in ["xq", "xueqiu", "XQ"]:
        return get_bar_fromxq(code, prev, interval)
    elif _from in ["IN", "cninvesting", "investing"]:
        return get_bar_frominvesting(code, prev, interval)
    elif _from in ["INA"]:
        return get_bar_frominvesting(code, prev, interval)
        # 这里 app 源是 404，只能用网页源
    else:
        raise ParserFailure("unrecoginized _from %s" % _from)


def get_bar_frominvesting(code, prev=120, interval=3600):
    """
    get bar data beyond daily bar

    :param code: str. investing id or url
    :param prev: int, data points from now, max might be around 500, if exceed, only None is returnd
    :param interval: default 3600. optional 60, 300, 900, 1800, 18000, 86400, "week", "month"
    :return: pd.DataFrame or None if prev and interval unmatch the API
    """
    if interval == "day":
        interval = 86400
    elif interval == "hour":
        interval = 3600
    elif interval == "minute":
        interval = 60
    elif interval == 86400 * 7:
        interval = "week"
    elif interval == 86400 * 30:
        interval = "month"
    if len(code.split("/")) == 2:
        code = get_investing_id(code)

    url = "https://cn.investing.com"
    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4)\
                AppleWebKit/537.36 (KHTML, like Gecko)",
        "Host": "cn.investing.com",
        "Referer": "https://cn.investing.com/commodities/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
    }

    r = rget(
        url
        + "/common/modules/js_instrument_chart/api/data.php?pair_id={code}&pair_id_for_news={code}\
&chart_type=area&pair_interval={interval}&candle_count={prev}&events=yes&volume_series=yes&period=".format(
            code=code, prev=str(prev), interval=str(interval)
        ),
        headers=headers,
    )
    if not r.text:
        return  # None
    r = r.json()
    df = pd.DataFrame(r["candles"], columns=["date", "close", "0", "1"])
    df = df.drop(["0", "1"], axis=1)
    df["date"] = df["date"].apply(
        lambda t: dt.datetime.fromtimestamp(t / 1000, tz=tz_bj).replace(tzinfo=None)
    )
    return df


def get_bar_fromxq(code, prev, interval=3600):
    """

    :param code:
    :param prev:
    :param interval: 1m, 5m, 15m, 30m, 60m, 120m, month, quarter, year, week, day
    :return:
    """
    # max interval is also around 500
    trans = {
        "60": "1m",
        "300": "5m",
        "900": "15m",
        "1800": "30m",
        "3600": "60m",
        "7200": "120m",
        "86400": "day",
        "604800": "week",
        "2592000": "month",
    }
    interval = trans.get(str(interval), interval)
    url = "https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol={code}&begin={tomorrow}&period={interval}&type=before\
&count=-{prev}&indicator=kline,pe,pb,ps,pcf,market_capital,agt,ggt,balance".format(
        code=code, tomorrow=int(tomorrow_ts() * 1000), prev=prev, interval=interval
    )
    r = rget(
        url, headers={"user-agent": "Mozilla/5.0"}, cookies={"xq_a_token": get_token()}
    )
    if not r.text:
        return  # None
    else:
        df = pd.DataFrame(r.json()["data"]["item"], columns=r.json()["data"]["column"])
        df["date"] = df["timestamp"].apply(
            lambda t: dt.datetime.fromtimestamp(t / 1000, tz=tz_bj).replace(tzinfo=None)
        )
        df = df[
            [
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "turnoverrate",
                "percent",
            ]
        ]
    return df


class vinfo(basicinfo, indicator):
    """
    vinfo is an info like class wrapper for get_daily, it behaves like info
    """

    def __init__(
        self, code, name=None, start=None, end=None, rate=0, col="close", **kws
    ):
        if not name:
            try:
                name = get_rt(code)["name"]
            except:
                name = code
        self.name = name
        self.code = code
        self.start = start  # None is one year ago
        self.end = end  # None is yesterday
        df = get_daily(code, start=start, end=end)
        df["totvalue"] = df[col]
        df["netvalue"] = df[col] / df.iloc[0][col]
        self.price = df
        self.round_label = kws.get("round_label", 0)
        self.dividend_label = kws.get("dividend_label", 0)
        self.value_label = kws.get("value_label", 1)  # 默认按金额赎回
        self.specialdate = []
        self.fenhongdate = []
        self.zhesuandate = []
        self.rate = rate


VInfo = vinfo
