# -*- coding: utf-8 -*-
"""
modules for universal fetcher that gives historical daily data for almost everything in the market
"""

import requests
import datetime as dt
import pandas as pd
from bs4 import BeautifulSoup

from xalpha.info import fundinfo, mfundinfo


def today_obj():
    now = dt.datetime.today()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def tomorrow_ts():
    dto = dt.datetime.now() + dt.timedelta(1)
    return dto.timestamp()


def get_token():
    r = requests.get("https://xueqiu.com", headers={"user-agent": "Mozilla"})
    return r.cookies["xq_a_token"]


def get_history(
    code, prefix="SH", count=365, token="a664afb60c7036c7947578ac1a5860c4cfb6b3b5"
):
    url = "https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol={prefix}{code}&begin={tomorrow}&period=day&type=before&count=-{count}"
    data = requests.get(
        url.format(
            code=code, prefix=prefix, tomorrow=int(tomorrow_ts() * 1000), count=count
        ),
        cookies={"xq_a_token": token},
        headers={"user-agent": "Mozilla/5.0"},
    )
    return data.json()


def ts2pdts(ts):
    dto = dt.datetime.fromtimestamp(ts / 1000)
    return dto.replace(hour=0, minute=0, second=0, microsecond=0)


def get_xueqiu(code, count):
    r = get_history(code=code, prefix="", count=count, token=get_token())
    df = pd.DataFrame(data=r["data"]["item"], columns=r["data"]["column"])
    df["date"] = (df["timestamp"]).apply(ts2pdts)  # reset hours to zero
    return df


def get_cninvesting(curr_id, st_date, end_date):
    rpost = requests.post(
        "https://cn.investing.com/instruments/HistoricalDataAjax",
        data={
            "curr_id": curr_id,
            #  "smlID": smlID,  # ? but seems to be fixed with curr_id, it turns out it doesn't matter
            "st_date": st_date,
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
    s = BeautifulSoup(rpost.text, "lxml")
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
    r = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36"
        },
    )
    s = BeautifulSoup(r.text, "lxml")
    pid = s.find("span", id="last_last")["class"][-1].split("-")[1]
    return pid


def get_rmb(start=None, end=None, prev=360, currency="USD/CNY"):
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
    if count <= 360:
        r = requests.post(
            url.format(start_str=start_str, end_str=end_str, currency=currency)
        )
        rl.extend(r.json()["records"])
    else:  # data more than 1 year cannot be fetched once due to API limitation
        sepo_obj = end_obj
        sepn_obj = sepo_obj - dt.timedelta(360)
        #         sep0_obj = end_obj - dt.timedelta(361)
        while sepn_obj > start_obj:  # [sepn sepo]
            r = requests.post(
                url.format(
                    start_str=sepn_obj.strftime("%Y-%m-%d"),
                    end_str=sepo_obj.strftime("%Y-%m-%d"),
                    currency=currency,
                )
            )
            rl.extend(r.json()["records"])

            sepo_obj = sepn_obj - dt.timedelta(1)
            sepn_obj = sepo_obj - dt.timedelta(360)
        r = requests.post(
            url.format(
                start_str=start_obj.strftime("%Y-%m-%d"),
                end_str=sepo_obj.strftime("%Y-%m-%d"),
                currency=currency,
            )
        )
        rl.extend(r.json()["records"])
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


def get_daily(code, start=None, end=None, prev=365, _from=None):
    """
    universal fetcher for daily historical data of literally everything has a value in market.
    数据来源包括天天基金，雪球，英为财情，外汇局官网

    :param code: str.
            1. 对于沪深市场的股票，指数，ETF，LOF 基金，可转债和债券，直接使用其代码，主要开头需要包括 SH 或者 SZ。
            2. 对于香港市场的股票，指数，使用其数字代码，同时开头要添加 HK。
            3. 对于美国市场的股票，指数，ETF 等，直接使用其字母缩写代码即可。
            4. 对于人民币中间价数据，使用 "USD/CNY" 的形式，具体可能的值可在 http://www.chinamoney.com.cn/chinese/bkccpr/ 历史数据的横栏查询
            5. 对于所有可以在 cn.investing.com 网站查到的金融产品，其代码可以是该网站对应的统一代码，或者是网址部分，比如 DAX 30 的概览页面为
                https://cn.investing.com/indices/germany-30，那么对应代码即为 "indices/germany-30"。也可去网页 inspect 手动查找其内部代码
                （一般不需要自己做，推荐直接使用网页url作为 code 变量值），手动 inspect 加粗的实时价格，其对应的网页 span class 中的 pid 的数值即为内部代码。
            6. 对于国内发行的基金，使用基金代码，同时开头添加 F。
            7. 对于国内发行的货币基金，使用基金代码，同时开头添加 M。（全部按照净值数据处理）
    :param start: str. "20200101", "2020/01/01", "2020-01-01" are all legal. The starting date of daily data.
    :param end: str. format is the same as start. The ending date of daily data.
    :param prev: Optional[int], default 365. If start is not specified, start = end-prev.
    :param _from: Optional[str]. can be one of "xueqiu", "zjj", "investing", "tiantianjijin". Only used for debug to
        enfore data source. For common use, _from can be chosed automatically based on code in the run time.
    :return: pd.Dataframe.
        must include cols: date[pd.Timestampe]，close[float64]。
    """
    if not end:
        end_obj = today_obj()
    else:
        end_obj = dstr2dobj(end)
    if not start:
        start_obj = end_obj - dt.timedelta(prev)
    else:
        start_obj = dstr2dobj(start)
    if not _from:
        if code.startswith("SH") or code.startswith("SZ"):
            _from = "xueqiu"
        elif code.endswith("/CNY"):
            _from = "zjj"
        elif len(code.split("/")) > 1:
            _from = "cninvesting"
            code = get_investing_id(code)
        elif code.isdigit():
            _from = "cninvesting"
        elif code[0] in ["F", "M"] and code[1:].isdigit():
            _from = "ttjj"
        elif code.startswith("HK") and code[2:].isdigit() and len(code) == 7:
            _from = "xueqiu"
            code = code[2:]
        else:
            _from = "xueqiu"

    count = (end_obj - start_obj).days + 1
    start_str = start_obj.strftime("%Y/%m/%d")
    end_str = end_obj.strftime("%Y/%m/%d")

    if _from in ["cninvesting", "investing", "default"]:
        df = get_cninvesting(code, start_str, end_str)
        return prettify(df)
    elif _from in ["xueqiu", "xq", "snowball"]:
        df = get_xueqiu(code, count)
        df = df[df.date < end_str]
        df = df[df.date > start_str]
        return prettify(df)
    elif _from in ["zhongjianjia", "zjj", "chinamoney"]:
        df = get_rmb(start, end, prev, currency=code)
        return df
    elif _from in ["ttjj", "tiantianjijin", "xalpha", "eastmoney"]:
        df = get_fund(code)
        df = df[df.date < end_str]
        df = df[df.date > start_str]
        return df


def _float(n):
    try:
        n = n.replace(",", "")
    except AttributeError:
        pass
    return float(n)
