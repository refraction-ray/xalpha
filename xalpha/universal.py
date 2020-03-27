# -*- coding: utf-8 -*-
"""
modules for universal fetcher that gives historical daily data and realtime data
for almost everything in the market
"""

import os
import sys
import datetime as dt
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from functools import wraps
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
    )

    # 本地导入
except ImportError:
    try:
        from jqdata import finance  # 云平台导入
    except ImportError:
        pass

from xalpha.info import fundinfo, mfundinfo
from xalpha.cons import rget, rpost, rget_json, rpost_json, yesterday, opendate
from xalpha.provider import data_source
from xalpha.exceptions import DataPossiblyWrong


thismodule = sys.modules[__name__]
xamodule = sys.modules["xalpha"]


def today_obj():
    now = dt.datetime.today()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def tomorrow_ts():
    dto = dt.datetime.now() + dt.timedelta(1)
    return dto.timestamp()


def get_token():
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
    tz_bj = dt.timezone(dt.timedelta(hours=8))
    dto = dt.datetime.fromtimestamp(ts / 1000, tz=tz_bj).replace(tzinfo=None)
    return dto.replace(
        hour=0, minute=0, second=0, microsecond=0
    )  # 雪球美股数据时间戳是美国0点，按北京时区换回时间后，把时分秒扔掉就重合了


def get_xueqiu(code, count):
    r = get_history(code=code, prefix="", count=count, token=get_token())
    df = pd.DataFrame(data=r["data"]["item"], columns=r["data"]["column"])
    df["date"] = (df["timestamp"]).apply(ts2pdts)  # reset hours to zero
    return df


def get_cninvesting(curr_id, st_date, end_date):
    r = rpost(
        "https://cn.investing.com/instruments/HistoricalDataAjax",
        data={
            "curr_id": curr_id,
            #  "smlID": smlID,  # ? but seems to be fixed with curr_id, it turns out it doesn't matter
            "st_date": st_date,  # %Y/%m/%d
            "end_date": end_date,
            "interval_sec": "Daily",
            "sort_col": "date",
            "sort_ord": "DESC",
            "action": "historical_data",
        },
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4)\
                AppleWebKit/537.36 (KHTML, like Gecko)",
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


def get_investing_id(suburl):
    url = "https://cn.investing.com"
    if not suburl.startswith("/"):
        url += "/"
    url += suburl
    r = rget(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36"
        },
    )
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


def get_rmb(start=None, end=None, prev=360, currency="USD/CNY"):
    """
    获取人民币汇率中间价, 该 API 官网数据源，稳定性很差

    :param start:
    :param end:
    :param prev:
    :param currency:
    :return: pd.DataFrame
    """
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
    return df


def get_fund(code):
    if code[0] == "F":
        df = fundinfo(code[1:]).price
    elif code[0] == "M":
        df = mfundinfo(code[1:]).price
    df["close"] = df["netvalue"]
    return df[["date", "close"]]


# this is the most elegant approach to dispatch get_daily, the definition can be such simple
# you actually don't need to bother on start end blah, it is all taken care of by ``cahcedio``
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
    df = pd.read_excel(url)
    # print(df.iloc[:10])
    df = df.iloc[6:]
    df["close"] = df["Unnamed: " + col]
    df["date"] = pd.to_datetime(df["Unnamed: 0"])
    df = df[["date", "close"]]
    return df


def get_historical_frombb(code, start=None, end=None, **kws):
    """
    https://www.bloomberg.com/ 数据源, 试验性支持。
    似乎有很严格的 IP 封禁措施, 且最新数据更新滞后，似乎难以支持 T-1 净值预测

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


def _get_daily(code, start=None, end=None, prev=365, _from=None, wrapper=True, **kws):
    """
    universal fetcher for daily historical data of literally everything has a value in market.
    数据来源包括天天基金，雪球，英为财情，外汇局官网，聚宽，标普官网，bloomberg 等。

    :param code: str.

            1. 对于沪深市场的股票，指数，ETF，LOF 场内基金，可转债和债券，直接使用其代码，主要开头需要包括 SH 或者 SZ。

            2. 对于香港市场的股票，指数，使用其数字代码，同时开头要添加 HK。

            3. 对于美国市场的股票，指数，ETF 等，直接使用其字母缩写代码即可。

            4. 对于人民币中间价数据，使用 "USD/CNY" 的形式，具体可能的值可在 http://www.chinamoney.com.cn/chinese/bkccpr/ 历史数据的横栏查询

            5. 对于所有可以在 cn.investing.com 网站查到的金融产品，其代码可以是该网站对应的统一代码，或者是网址部分，比如 DAX 30 的概览页面为 https://cn.investing.com/indices/germany-30，那么对应代码即为 "indices/germany-30"。也可去网页 inspect 手动查找其内部代码（一般不需要自己做，推荐直接使用网页url作为 code 变量值），手动 inspect 加粗的实时价格，其对应的网页 span class 中的 pid 的数值即为内部代码。

            6. 对于国内发行的基金，使用基金代码，同时开头添加 F。

            7. 对于国内发行的货币基金，使用基金代码，同时开头添加 M。（全部按照净值数据处理）

            8. 形如 peb-000807.XSHG 或 peb-SH000807 格式的数据，可以返回每周的指数估值情况，需要 enable 聚宽数据源方可查看。

            9. 形如 iw-000807.XSHG 或 peb-SH000807 格式的数据，可以返回每月的指数成分股和实时权重，需要 enable 聚宽数据源方可查看。

            10. 形如 fs-SH501018 格式的数据，可以返回指定场内基金每日份额，需要 enable 聚宽数据源方可查看。

            11. 形如 SP5475707.2 格式的数据，可以返回标普官网相关指数的日线数据（最近十年），id 5475707 部分可以从相关指数 export 按钮获取的链接中得到，小数点后的部分代表保存的列数。参考链接：https://us.spindices.com/indices/equity/sp-global-oil-index

            12. 形如 BB-FGERBIU:ID 格式的数据，对应网页 https://www.bloomberg.com/quote/FGERBIU:ID，可以返回彭博的数据（最近五年）

    :param start: str. "20200101", "2020/01/01", "2020-01-01" are all legal. The starting date of daily data.
    :param end: str. format is the same as start. The ending date of daily data.
    :param prev: Optional[int], default 365. If start is not specified, start = end-prev.
    :param _from: Optional[str]. 一般用户不需设定该选项。can be one of "xueqiu", "zjj", "investing", "tiantianjijin". Only used for debug to
        enfore data source. For common use, _from can be chosed automatically based on code in the run time.
    :param wrapper: bool. 一般用户不需设定该选项。
    :return: pd.Dataframe.
        must include cols: date[pd.Timestamp]，close[float64]。
    """
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
        elif len(code[1:].split("/")) == 2:
            _from = "cninvesting"
            code = get_investing_id(code)
        elif code.isdigit():
            _from = "cninvesting"
        elif code[0] in ["F", "M"] and code[1:].isdigit():
            _from = "ttjj"
        elif code.startswith("HK") and code[2:].isdigit() and len(code) == 7:
            _from = "xueqiu"
            code = code[2:]
        elif code.startswith("SP") and code[2:].split(".")[0].isdigit():
            _from = "SP"
        elif len(code.split("-")) == 2 and len(code.split("-")[0]) <= 3:
            # peb-000807.XSHG
            _from = code.split("-")[0]
            code = code.split("-")[1]
        else:
            _from = "xueqiu"

    count = (today_obj() - start_obj).days + 1
    start_str = start_obj.strftime("%Y/%m/%d")
    end_str = end_obj.strftime("%Y/%m/%d")

    if _from in ["cninvesting", "investing", "default"]:
        df = get_cninvesting(code, start_str, end_str)
        df = prettify(df)
    elif _from in ["xueqiu", "xq", "snowball"]:
        df = get_xueqiu(code, count)
        df = prettify(df)
    elif _from in ["zhongjianjia", "zjj", "chinamoney"]:
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
    q_ext = r["data"]["quote"].get("current_ext", None)
    percent = r["data"]["quote"]["percent"]
    currency = r["data"]["quote"]["currency"]
    return {
        "name": n,
        "current": _float(q),
        "percent": _float(percent),
        "current_ext": _float(q_ext) if q_ext else None,
        "currency": currency,
    }


def get_cninvesting_rt(suburl):
    url = "https://cn.investing.com"
    if not suburl.startswith("/"):
        url += "/"
    url += suburl
    r = rget(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36"
        },
    )
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
    return {
        "name": name,
        "current": q,
        "current_ext": q_ext,
        "currency": currency,
        "percent": percent,
    }


def get_rt_from_sina(code):
    if (
        code.startswith("SH") or code.startswith("SZ") or code.startswith("HK")
    ) and code[2:].isdigit():
        tinycode = code[:2].lower() + code[2:]
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
        d["current"] = float(l[3])
        d["percent"] = round((float(l[3]) / float(l[2]) - 1) * 100, 2)
        d["current_ext"] = None
        if code.startswith("HK"):
            d["currency"] = "HKD"
        else:
            d["currency"] = "CNY"
    else:
        d["currency"] = "USD"
        d["current"] = float(l[1])
        d["percent"] = float(l[2])
        d["current_ext"] = None
    return d


def get_rt(code, _from=None, double_check=False, double_check_threhold=0.005):
    """
    universal fetcher for realtime price of literally everything.

    :param code: str. 规则同 :func:`get_daily`. 需要注意场外基金和外汇中间价是不支持实时行情的，因为其每日只有一个报价。对于 investing 的数据源，只支持网址格式代码。
    :param _from: Optional[str]. can be one of "xueqiu", "investing". Only used for debug to
        enfore data source. For common use, _from can be chosed automatically based on code in the run time.
    :param double_check: Optional[bool], default False. 如果设为 True，只适用于 A 股，美股，港股实时行情，会通过至少两个不同的数据源交叉验证，确保正确。
            适用于需要自动交易等情形，防止实时数据异常。
    :return: Dict[str, Any].
        包括 "name", "current", "percent" 三个必有项和 "current_ext"（盘后价格）, "currency" （计价货币）两个值可能为 ``None`` 的选项。
    """
    if not _from:
        if len(code.split("/")) > 1:
            _from = "investing"
        # elif code.startswith("HK") and code[2:].isdigit():
        #     _from = "xueqiu"
        else:  # 默认不启用新浪实时，只做双重验证
            _from = "xueqiu"
    if _from in ["cninvesting", "investing"]:
        return get_cninvesting_rt(code)
    elif double_check:
        r1 = get_xueqiu_rt(code, token=get_token())
        r2 = get_rt_from_sina(code)
        if abs(r1["current"] / r2["current"] - 1) > double_check_threhold:
            raise DataPossiblyWrong("realtime data unmatch for %s" % code)
        return r1
    elif _from in ["xueqiu", "xq", "snowball"]:
        return get_xueqiu_rt(code, token=get_token())
    elif _from in ["sina", "sn", "xinlang"]:
        return get_rt_from_sina(code)


get_realtime = get_rt


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
                            df1 = f(*args, **kws)
                            if len(df1) > 0:
                                df1 = df1[df1["date"] <= kws["end"]]
                            if len(df1) > 0:
                                is_changed = True
                                df0 = df1.append(df0, ignore_index=True)
                        # 向后延拓
                        if df0.iloc[-1][date] < end_obj:
                            if len(df0[df0["date"] == df0.iloc[-1]["date"]]) == 1:
                                kws["start"] = (df0.iloc[-1][date]).strftime("%Y%m%d")
                            else:
                                kws["start"] = (
                                    df0.iloc[-1][date] + dt.timedelta(days=1)
                                ).strftime("%Y%m%d")
                            kws["end"] = end_str
                            df2 = f(*args, **kws)
                            if len(df2) > 0:
                                df2 = df2[df2["date"] >= kws["start"]]
                            if len(df2) > 0:
                                is_changed = True
                                if len(df0[df0["date"] == df0.iloc[-1]["date"]]) == 1:
                                    df0 = df0.iloc[:-1]
                                df0 = df0.append(df2, ignore_index=True)
                            # 注意这里抹去更新了原有最后一天的缓存，这是因为日线最新一天可能有实时数据污染

                    except (FileNotFoundError, exc.ProgrammingError, KeyError):
                        if precached:
                            kws["start"] = precached.replace("/", "").replace("-", "")
                            kws["end"] = (today_obj() - dt.timedelta(days=1)).strftime(
                                "%Y-%m-%d"
                            )
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

            if df0 is not None:
                df0 = df0[df0["date"] <= end_str]
                df0 = df0[df0["date"] >= start_str]

            return df0

        return wrapper

    return cached


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
        print("call", d, " ", code)
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
        print("compute pe pb on %s" % d)
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
    #     df = get_fundamentals(q, date)
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
