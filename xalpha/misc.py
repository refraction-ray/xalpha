# -*- coding: utf-8 -*-
"""
modules for misc crawler without unfied API
"""

import re
import pandas as pd
import datetime as dt
from bs4 import BeautifulSoup

from xalpha.cons import rget, rget_json, today_obj, region_trans
from xalpha.universal import lru_cache_time, _float
from xalpha.exceptions import ParserFailure

# 该模块只是保存其他一些爬虫的函数，其接口很不稳定，不提供文档和测试，且随时增删，慎用！


@lru_cache_time(ttl=7200, maxsize=64)
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
