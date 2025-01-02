# -*- coding: utf-8 -*-
"""
basic constants and utility functions
"""

import datetime as dt
import os
import time
import logging
import inspect
import json
from decimal import Decimal
import requests
from functools import wraps
from simplejson.errors import JSONDecodeError

import pandas as pd
from pyecharts.options import (
    AxisOpts,
    DataZoomOpts,
    LegendOpts,
    TooltipOpts,
    VisualMapOpts,
)
from numpy import sqrt
from scipy import optimize

from xalpha import __path__
from .exceptions import HttpStatusError

logger = logging.getLogger(__name__)

# date obj of today
# today = lambda: dt.datetime.combine(dt.date.today(), dt.time.min)

tz_bj = dt.timezone(dt.timedelta(hours=8))


def today_obj():
    """
    today obj in beijing timezone with no tzinfo

    :return: datetime.datetime
    """
    now = dt.datetime.now(tz=tz_bj)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)


# datetime obj for yesterdate date with time set to be 0:0:0
yesterdayobj = lambda: (dt.datetime.now(tz_bj).replace(tzinfo=None) - dt.timedelta(1))

# string for yesterday, only used for indexinfo url
yesterday = lambda: dt.datetime.strftime(yesterdayobj(), "%Y%m%d")

# string for yesterday with dash
yesterdaydash = lambda: dt.datetime.strftime(yesterdayobj(), "%Y-%m-%d")


# list: all the trade date of domestic stock market in the form of string
# update per year by ``xa.misc.update_caldate("xalpha/caldate.csv", "2023")``
caldate = pd.read_csv(os.path.join(__path__[0], "caldate.csv"))
# data source
# pro = ts.pro_api()
# df = pro.trade_cal(exchange='', start_date='20230101', end_date='20231231')
opendate = list(caldate[caldate["is_open"] == 1]["cal_date"])
# opendate = list(ts.trade_cal()[ts.trade_cal()['isOpen']==1]['calendarDate'])
opendate_set = set(opendate)  # for speed checking?

# fund code list which always round down for the purchase share approximation
droplist = ["003318", "000311", "000601", "009989"]

sqrt_days_in_year = sqrt(250.0)


def calendar_selfcheck():
    # 国内链接 githubusercontent.com 大概率存在问题，因此设计成联网自动更新日历大概率无用。
    # 也许之后考虑一些较稳定的第三方资源托管服务
    current_year = dt.datetime.now().year
    if str(current_year) != opendate[-1][:4]:
        logger.warning(
            "Please update xalpha via `pip install -U xalpha` to keep the trade calendar up-to-date"
        )
        print(
            "请更新 xalpha 版本以更新最新年份的 A 股交易日历, 否则将可能无法正确获取和处理最新的基金净值"
        )


calendar_selfcheck()


region_trans = {
    "瑞士": "CH",
    "日本": "JP",
    "韩国": "KR",
    "美国": "US",
    "香港": "HK",
    "中国香港": "HK",
    "德国": "DE",
    "英国": "UK",
    "法国": "FR",
    "中国": "CN",
    "墨西哥": "MX",
    "澳大利亚": "AU",
    "新加坡": "SG",
    "印度": "IN",
    "台湾": "TW",
    "中国台湾": "TW",
}


connection_errors = (
    HttpStatusError,
    ConnectionResetError,
    requests.exceptions.RequestException,
    requests.exceptions.ConnectionError,
    requests.exceptions.SSLError,
    JSONDecodeError,
)

line_opts = {
    "datazoom_opts": [
        DataZoomOpts(is_show=True, type_="slider", range_start=50, range_end=100),
        DataZoomOpts(
            is_show=True,
            type_="slider",
            orient="vertical",
            range_start=50,
            range_end=100,
        ),
    ],
    "tooltip_opts": TooltipOpts(
        is_show=True, trigger="axis", trigger_on="mousemove", axis_pointer_type="cross"
    ),
}

heatmap_opts = {
    "visualmap_opts": VisualMapOpts(
        min_=-1, max_=1, orient="horizontal", pos_right="middle", pos_top="bottom"
    )
}

# pie_opts = {
#     "tooltip_opts": TooltipOpts(),
#     "legend_opts": LegendOpts(orient="vertical", pos_left="left"),
# }

themeriver_opts = {
    "xaxis_opts": AxisOpts(type_="time"),
    "datazoom_opts": [DataZoomOpts(range_start=60, range_end=100)],
    "tooltip_opts": TooltipOpts(trigger_on="mousemove", trigger="item"),
    "legend_opts": LegendOpts(pos_top="top"),
}


def xnpv(rate, cashflows):
    """
    give the current cash value based on future cashflows

    :param rate: float, the preset year rate
    :param cashflows: a list, in which each element is a tuple of the form (date, amount),
        where date is a datetime object and amount is an integer or floating number.
        Cash outflows (investments) are represented with negative amounts,
        and cash inflows (returns) are positive amounts.
    :returns: a single float value which is the NPV of the given cash flows
    """
    chron_order = sorted(cashflows, key=lambda x: x[0])
    t0 = chron_order[0][0]
    return sum([cf / (1 + rate) ** ((t - t0).days / 365.0) for (t, cf) in chron_order])


def xirr(cashflows, guess=0.1):
    """
    calculate the Internal Rate of Return of a series of cashflows at irregular intervals.

    :param cashflows: a list, in which each element is a tuple of the form (date, amount),
        where date is a datetime object and amount is an integer or floating number.
        Cash outflows (investments) are represented with negative amounts,
        and cash inflows (returns) are positive amounts.
    :param guess: floating number, a guess at the xirr rate solution to be used
        as a starting point for the numerical solution
    :returns: the IRR as a single floating number
    """
    return optimize.newton(lambda r: xnpv(r, cashflows), guess)


def myround(num, label=1):
    """
    correct implementation of round with round half up, round to 2 decimals

    :param num: the floating number, to be rounded
    :param label: integer 1 or 2, 1 for round half up while 2 for always round down
    :returns: the float number after rounding, with two decimals
    """
    if label == 1:
        res = float(
            Decimal(str(num)).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
        )
    elif (
        label == 2
    ):  # for jingshunchangcheng... who just omit the overflow share behind 2 decimal
        res = float(Decimal(str(num)).quantize(Decimal("0.01"), rounding="ROUND_DOWN"))
    return res


def convert_date(date):
    """
    convert date into datetime object

    :param date: string of form '2017-01-01' or datetime object
    :returns: corresponding datetime object
    """
    if isinstance(date, str):
        return pd.Timestamp(date)
    else:
        return date


def _date_check(dtobj, check=False):
    if not isinstance(dtobj, dt.datetime):
        dtobj = dt.datetime.strptime(dtobj.replace("/", "").replace("-", ""), "%Y%m%d")
    if check and (dtobj.year > dt.datetime.now().year or dtobj.year < 1991):
        raise ValueError(
            "date goes beyond market range: %s" % dtobj.strftime("%Y-%m-%d")
        )
    return dtobj


def next_onday(dtobj):
    dtobj = _date_check(dtobj, check=True)
    dtobj += dt.timedelta(1)
    while dtobj.strftime("%Y-%m-%d") not in opendate_set:
        dtobj += dt.timedelta(1)
    return dtobj


def last_onday(dtobj):
    dtobj = _date_check(dtobj, check=True)
    dtobj -= dt.timedelta(1)
    while dtobj.strftime("%Y-%m-%d") not in opendate_set:
        dtobj -= dt.timedelta(1)
    return dtobj


def avail_dates(dtlist, future=False):
    """
    make every day in the list the next open day

    :param dtlist: datetime obj list
    :param future: bool, default False, indicating the latest day in the list is yesterday
    :return: datetime obj list
    """
    ndtlist = []
    for d in dtlist:
        if d.strftime("%Y-%m-%d") not in opendate_set:
            nd = next_onday(d)
        else:
            nd = d
        if future is False:
            if (nd - yesterdayobj()).days > 0:
                continue
        ndtlist.append(nd)
    return ndtlist


def scale_dict(d, scale=1, ulimit=100, dlimit=50, aim=None):
    t = sum([v for _, v in d.items()])
    if t * scale > ulimit:
        scale = ulimit / t
    elif t * scale < dlimit:
        scale = dlimit / t
    if aim:
        scale = aim / t
    for k, v in d.items():
        d[k] = v * scale
    return d


def _float(n):
    try:
        n = n.replace(",", "")
        if n.endswith("K") or n.endswith("k"):
            n = float(n[:-1]) * 1000
        elif n.endswith("M") or n.endswith("m"):
            n = float(n[:-1]) * 1000 * 1000
        elif n.endswith("G") or n.endswith("g") or n.endswith("B") or n.endswith("b"):
            n = float(n[:-1]) * 1000 * 1000 * 1000
        elif n == "-":
            logger.info("_float met -, taken as 0")
            return 0
        elif n.endswith("%"):
            logger.info("_float met with %% as %s" % n)
            return float(n[:-1]) / 100
    except AttributeError:
        pass
    if not n:
        logger.info("_float met with None as input arguments")
        return 0.0
    return float(n)


def reconnect(tries=5, timeout=12):
    def robustify(f):
        @wraps(f)
        def wrapper(*args, **kws):
            import xalpha.provider as xp

            if getattr(xp, "proxy", None):
                kws["proxies"] = {"http": xp.proxy, "https": xp.proxy}
                kws["timeout"] = timeout
                logger.debug("Using proxy %s" % xp.proxy)
            if args:
                url = args[0]
            else:
                url = kws.get("url", "")
            headers = kws.get("headers", {})
            if (not headers.get("user-agent", None)) and (
                not headers.get("User-Agent", None)
            ):
                headers["user-agent"] = "Mozilla/5.0"
            kws["headers"] = headers
            for count in range(tries):
                try:
                    logger.debug(
                        "Fetching url: %s . Inside function `%s`"
                        % (url, inspect.stack()[1].function)
                    )
                    r = f(*args, **kws)
                    if (
                        getattr(r, "status_code", 200) != 200
                    ):  # in case r is a json dict
                        raise HttpStatusError
                    return r
                except connection_errors as e:
                    logger.warning("Fails at fetching url: %s. Try again." % url)
                    if count == tries - 1:
                        logger.error(
                            "Still wrong at fetching url: %s. after %s tries."
                            % (url, tries)
                        )
                        logger.error("Fails due to %s" % e.args[0])
                        raise e
                    time.sleep(0.5 * count)

        return wrapper

    return robustify


rget = reconnect()(requests.get)
rpost = reconnect()(requests.post)


@reconnect()
def rget_json(*args, **kws):
    r = requests.get(*args, **kws)
    return r.json()


@reconnect()
def rpost_json(*args, **kws):
    r = requests.post(*args, **kws)
    return r.json()


# def rget(*args, **kws):
#     tries = 5
#     for count in range(tries):
#         try:
#             r = requests.get(*args, **kws)
#             return r
#         except connection_errors as e:
#             if count == tries - 1:
#                 print(*args, sep="\n")
#                 print("still wrong after several tries")
#                 raise e
#             time.sleep(0.5*count)
#
#
# def rget_json(*args, **kws):
#     tries = 5
#     for count in range(tries):
#         try:
#             r = requests.get(*args, **kws)
#             return r.json()
#         except connection_errors as e:
#             if count == tries - 1:
#                 print(*args, sep="\n")
#                 print("still wrong after several tries")
#                 raise e
#             time.sleep(0.5*count)
#
#
# def rpost(*args, **kws):
#     tries = 5
#     for count in range(tries):
#         try:
#             r = requests.post(*args, **kws)
#             return r
#         except connection_errors as e:
#             if count == tries - 1:
#                 print(*args, sep="\n")
#                 print("still wrong after several tries")
#                 raise e
#             time.sleep(0.5*count)
#
#
# def rpost_json(*args, **kws):
#     tries = 5
#     for count in range(tries):
#         try:
#             r = requests.post(*args, **kws)
#             return r.json()
#         except connection_errors as e:
#             if count == tries - 1:
#                 print(*args, sep="\n")
#                 print("still wrong after several tries")
#                 raise e
#             time.sleep(0.5*count)

# extract from xa.misc.get_tdx_holidays
with open(os.path.join(__path__[0], "holiday.json"), "r") as f:
    holidays = json.load(f)

## simple subsitution for holdings.py

holdings = {}
holdings["501018"] = {
    "etfs/etfs-brent-1mth-uk": 17.51,
    "etfs/etfs-brent-crude": 15.04,
    "etfs/etfs-crude-oil": 7.34,
    "etfs/ipath-series-b-sp-gsci-crd-oil-tr": 0.06,
    "etfs/powershares-db-oil-fund": 11.6,
    "etfs/ubs-cmci-oil-sf-usd": 8.68,
    "etfs/united-states-12-month-oil": 8.14,
    "etfs/united-states-brent-oil-fund-lp": 15.42,
    "etfs/united-states-oil-fund": 9.63,
}
holdings["501018rt"] = {
    "commodities/brent-oil": {"weight": 49, "time": -1},
    "commodities/crude-oil": {"weight": 45, "time": 4},
}
