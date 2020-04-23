# -*- coding: utf-8 -*-
"""
modules for misc crawler without unfied API
"""

import re
import pandas as pd
import datetime as dt
import logging
import numpy as np
from scipy import stats
from bs4 import BeautifulSoup
from functools import lru_cache

logger = logging.getLogger(__name__)

from xalpha.cons import rget, rget_json, today_obj, region_trans, _float
from xalpha.universal import lru_cache_time
from xalpha.exceptions import ParserFailure

# 该模块只是保存其他一些爬虫的函数，其接口很不稳定，不提供文档和测试，且随时增删，慎用！


@lru_cache_time(ttl=600, maxsize=64)
def get_ri_status(suburl=None):
    if not suburl:
        suburl = "m=cb&a=cb_all"  # 可转债

    url = "http://www.richvest.com/index.php?"
    url += suburl
    r = rget(url, headers={"user-agent": "Mozilla/5.0"})
    b = BeautifulSoup(r.text, "lxml")
    cl = []
    for c in b.findAll("th"):
        cl.append(c.text)
    nocl = len(cl)
    rl = []
    for i, c in enumerate(b.findAll("td")):
        if i % nocl == 0:
            r = []
        r.append(c.text)
        if i % nocl == nocl - 1:
            rl.append(r)
    return pd.DataFrame(rl, columns=cl)


@lru_cache_time(ttl=7200, maxsize=512)
def get_sh_status(category="cb", date=None):
    url = "http://query.sse.com.cn/commonQuery.do?jsonCallBack=&"
    if category in ["cb", "kzz"]:
        url += "isPagination=false&sqlId=COMMON_BOND_KZZFLZ_ALL&KZZ=1"
    elif category in ["fund", "fs"]:
        if not date:
            date = today_obj().strftime("%Y%m%d")
        date = date.replace("/", "").replace("-", "")
        url += "&sqlId=COMMON_SSE_FUND_LOF_SCALE_CX_S&pageHelp.pageSize=10000&FILEDATE={date}".format(
            date=date
        )
    else:
        raise ParserFailure("unrecoginzed category %s" % category)

    r = rget_json(
        url,
        headers={
            "user-agent": "Mozilla/5.0",
            "Host": "query.sse.com.cn",
            "Referer": "http://www.sse.com.cn/market/bonddata/data/convertible/",
        },
    )
    return pd.DataFrame(r["result"])


@lru_cache_time(ttl=7200, maxsize=512)
def get_sz_status(category="cb", date=None):
    if not date:
        date = today_obj().strftime("%Y%m%d")
    date = date.replace("/", "").replace("-", "")
    date = date[:4] + "-" + date[4:6] + "-" + date[6:]
    url = "http://www.szse.cn/api/report/ShowReport/data?"
    if category in ["cb", "kzz"]:
        url += "SHOWTYPE=JSON&CATALOGID=1277&TABKEY=tab1&txtDate={date}".format(
            date=date
        )
        r = rget_json(url)
        df = pd.DataFrame(r[0]["data"])
        if len(df) == 0:
            return
        pcode = re.compile(r".*&DM=([\d]*)&.*")
        pname = re.compile(r"^([^&]*)&.*")
        df["证券代码"] = df["kzjcurl"].apply(lambda s: re.match(pcode, s).groups()[0])
        df["证券简称"] = df["kzjcurl"].apply(lambda s: re.match(pname, s).groups()[0])
        df["上市日期"] = pd.to_datetime(df["ssrq"])
        df["发行量"] = df["fxlnew"]
        df["换股价格"] = df["kzjg"]
        df["未转股数量"] = df["kzsl"]
        df["未转股比例"] = df["kzbl"]
        df["转股截止日期"] = pd.to_datetime(df["kzzzrq"])
        df = df[["证券代码", "证券简称", "上市日期", "发行量", "换股价格", "未转股数量", "未转股比例", "转股截止日期"]]
        return df


@lru_cache_time(ttl=7200, maxsize=512)
def get_sz_fs(code):
    url = "http://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&\
CATALOGID=1945_LOF&txtQueryKeyAndJC={code}".format(
        code=code
    )
    r = rget_json(url)
    return _float(r[0]["data"][0]["dqgm"]) * 1e4


def get_tdx_holidays(holidays=None, format="%Y-%m-%d"):
    r = rget("https://www.tdx.com.cn/url/holiday/")
    r.encoding = "gbk"
    b = BeautifulSoup(r.text, "lxml")
    l = b.find("textarea").string.split("\n")
    if not holidays:
        holidays = {}
    for item in l:
        if item.strip():
            c = item.split("|")
            if c[2] in region_trans:
                rg = region_trans[c[2]]
                tobj = dt.datetime.strptime(c[0], "%Y%m%d")
                tstr = tobj.strftime(format)
                if rg not in holidays:
                    holidays[rg] = [tstr]
                else:
                    holidays[rg].append(tstr)
    return holidays


def get_163_fundamentals(code, category="lrb"):
    # category xjllb zcfzb
    url = "http://quotes.money.163.com/service/{category}_{code}.html".format(
        category=category, code=code
    )
    logger.debug("Fetching from %s . in `get_163_fundamentals`" % url)
    df = pd.read_csv(url, encoding="gbk")
    df = df.set_index("报告日期")
    return df.T


@lru_cache()
def get_ttjj_suggestions(keyword):
    url = "http://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?callback=&m=1&key={key}".format(
        key=keyword
    )
    r = rget_json(url)
    return r["Datas"]


def get_bar_from_wsj(code, token=None, freq="1H"):
    # proxy required
    # code = "FUTURE/US/XNYM/CLM20"
    if not token:
        token = "cecc4267a0194af89ca343805a3e57af"
    # the thing I am concerned here is whether token is refreshed

    params = {
        "json": '{"Step":"PT%s","TimeFrame":"D5","EntitlementToken":"%s",\
"IncludeMockTick":true,"FilterNullSlots":false,"FilterClosedPoints":true,"IncludeClosedSlots":false,\
"IncludeOfficialClose":true,"InjectOpen":false,"ShowPreMarket":false,"ShowAfterHours":false,\
"UseExtendedTimeFrame":false,"WantPriorClose":true,"IncludeCurrentQuotes":false,\
"ResetTodaysAfterHoursPercentChange":false,\
"Series":[{"Key":"%s","Dialect":"Charting","Kind":"Ticker","SeriesId":"s1","DataTypes":["Last"]}]}'
        % (freq, token, code),
        "ckey": token[:10],
    }
    r = rget_json(
        "https://api-secure.wsj.net/api/michelangelo/timeseries/history",
        params=params,
        headers={
            "user-agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Dylan2010.EntitlementToken": token,
            "Host": "api-secure.wsj.net",
            "Origin": "https://www.marketwatch.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
        },
    )

    df = pd.DataFrame(
        {
            "date": r["TimeInfo"]["Ticks"],
            "close": [n[0] for n in r["Series"][0]["DataPoints"]],
        }
    )
    df["date"] = pd.to_datetime(df["date"] * 1000000) + pd.Timedelta(hours=8)
    df = df[df["close"] > -100.0]
    return df


## some small tools and calculators


def BlackScholes(S, K, t, v, r=0.03, CallPutFlag="C"):
    """
    BS option pricing calculator

    :param S: current stock price
    :param K: stricking price
    :param t: Time until option exercise (years to maturity)
    :param r: risk-free interest rate (by year)
    :param v: Variance(volitility) of annual increase
    :param CallPutFlag: "C" or "P", default call option
    :return:
    """
    # function modified from https://github.com/boyac/pyOptionPricing

    def CND(X):
        return stats.norm.cdf(X)

    d1 = (np.log(S / K) + (r + (v ** 2) / 2) * t) / (v * np.sqrt(t))
    d2 = d1 - v * np.sqrt(t)

    if CallPutFlag in ["c", "C"]:
        return S * CND(d1) - K * np.exp(-r * t) * CND(d2)  # call option
    elif CallPutFlag in ["p", "P"]:
        return K * np.exp(-r * t) * CND(-d2) - S * CND(-d1)  # put option
    else:
        raise ValueError("Unknown CallPutFlag %s" % CallPutFlag)
