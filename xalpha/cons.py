# -*- coding: utf-8 -*-
"""
basic constants and utility functions
"""

import datetime as dt
import os
import time
import logging
import inspect
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
from scipy import optimize

from xalpha import __path__

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
caldate = pd.read_csv(os.path.join(__path__[0], "caldate.csv"))
opendate = list(caldate[caldate["is_open"] == 1]["cal_date"])
# opendate = list(ts.trade_cal()[ts.trade_cal()['isOpen']==1]['calendarDate'])
opendate_set = set(opendate)  # for speed checking?

# fund code list which always round down for the purchase share approximation
droplist = ["003318", "000311"]

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

# extract from xa.misc.get_tdx_holidays
holidays = {
    "AU": [
        "2020-01-01",
        "2020-01-27",
        "2020-04-10",
        "2020-04-13",
        "2020-04-25",
        "2020-06-08",
        "2020-12-24",
        "2020-12-25",
        "2020-12-28",
        "2020-12-31",
    ],
    "CH": [
        "2020-01-01",
        "2020-01-02",
        "2020-04-10",
        "2020-04-13",
        "2020-05-01",
        "2020-05-21",
        "2020-06-01",
        "2020-12-24",
        "2020-12-25",
        "2020-12-31",
    ],
    "CN": [
        "2020-01-01",
        "2020-01-24",
        "2020-01-27",
        "2020-01-28",
        "2020-01-29",
        "2020-01-30",
        "2020-01-31",
        "2020-04-06",
        "2020-05-01",
        "2020-05-04",
        "2020-05-05",
        "2020-06-25",
        "2020-06-26",
        "2020-10-01",
        "2020-10-02",
        "2020-10-05",
        "2020-10-06",
        "2020-10-07",
        "2020-10-08",
    ],
    "DE": [
        "2020-01-01",
        "2020-04-10",
        "2020-04-13",
        "2020-05-01",
        "2020-06-01",
        "2020-12-24",
        "2020-12-25",
        "2020-12-31",
    ],
    "FR": [
        "2020-01-01",
        "2020-04-10",
        "2020-04-13",
        "2020-05-01",
        "2020-12-24",
        "2020-12-25",
        "2020-12-31",
    ],
    "HK": [
        "2020-01-01",
        "2020-01-27",
        "2020-01-28",
        "2020-04-10",
        "2020-04-13",
        "2020-04-30",
        "2020-05-01",
        "2020-06-25",
        "2020-07-01",
        "2020-10-01",
        "2020-10-02",
        "2020-10-26",
        "2020-12-25",
    ],
    "IN": [
        "2020-02-21",
        "2020-03-10",
        "2020-04-02",
        "2020-04-06",
        "2020-04-10",
        "2020-04-14",
        "2020-05-01",
        "2020-05-25",
        "2020-10-02",
        "2020-11-16",
        "2020-11-30",
        "2020-12-25",
    ],
    "JP": [
        "2020-01-01",
        "2020-01-02",
        "2020-01-03",
        "2020-01-13",
        "2020-02-11",
        "2020-02-24",
        "2020-03-20",
        "2020-04-29",
        "2020-05-04",
        "2020-05-05",
        "2020-05-06",
        "2020-07-23",
        "2020-07-24",
        "2020-08-10",
        "2020-09-21",
        "2020-09-22",
        "2020-11-03",
        "2020-11-23",
        "2020-12-31",
    ],
    "KR": [
        "2020-01-01",
        "2020-01-24",
        "2020-01-27",
        "2020-04-30",
        "2020-05-01",
        "2020-05-05",
        "2020-09-30",
        "2020-10-01",
        "2020-10-02",
        "2020-10-09",
        "2020-12-25",
        "2020-12-31",
    ],
    "SG": [
        "2020-01-01",
        "2020-01-24",
        "2020-04-10",
        "2020-05-01",
        "2020-05-07",
        "2020-05-21",
        "2020-07-31",
        "2020-08-10",
        "2020-12-24",
        "2020-12-25",
        "2020-12-31",
    ],
    "TW": [
        "2020-01-01",
        "2020-01-21",
        "2020-01-22",
        "2020-01-23",
        "2020-01-24",
        "2020-01-27",
        "2020-01-28",
        "2020-01-29",
        "2020-02-28",
        "2020-04-02",
        "2020-04-03",
        "2020-05-01",
        "2020-06-25",
        "2020-06-26",
        "2020-10-01",
        "2020-10-02",
        "2020-10-09",
    ],
    "UK": [
        "2020-01-01",
        "2020-04-10",
        "2020-04-13",
        "2020-05-08",
        "2020-05-25",
        "2020-08-31",
        "2020-12-24",
        "2020-12-25",
        "2020-12-28",
        "2020-12-31",
        "2021-01-01",
    ],
    "US": [
        "2020-01-01",
        "2020-01-20",
        "2020-02-17",
        "2020-03-08",
        "2020-04-10",
        "2020-05-25",
        "2020-07-03",
        "2020-09-07",
        "2020-11-01",
        "2020-11-26",
        "2020-11-27",
        "2020-12-24",
        "2020-12-25",
        "2021-01-01",
    ],
}

connection_errors = (
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
    if check and (dtobj.year > 2020 or dtobj.year < 1991):
        # TODO: remember change 2020 every year!
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
    while dtobj.strftime("%Y-%m-%d") not in opendate:
        dtobj -= dt.timedelta(1)
    return dtobj


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
            logger.warning("_float met with % as %s" % n)
            return float(n[:-1] / 100)
    except AttributeError:
        pass
    if not n:
        logger.warning("_float met with None as input arguments")
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
