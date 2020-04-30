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

from xalpha.cons import (
    rget,
    rpost,
    rget_json,
    rpost_json,
    today_obj,
    region_trans,
    last_onday,
    _float,
    xnpv,
    xirr,
)
import xalpha.universal as xu
from xalpha.universal import lru_cache_time, get_rt, ttjjcode
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
        pageno = 1
        data = []
        while True:
            suburl = "SHOWTYPE=JSON&CATALOGID=1277&TABKEY=tab1&PAGENO={pageno}&txtDate={date}".format(
                date=date, pageno=pageno
            )
            r = rget_json(url + suburl)
            if r[0]["data"]:
                data.extend(r[0]["data"])
                pageno += 1
            else:
                break
        # df = pd.DataFrame(r[0]["data"])
        df = pd.DataFrame(data)
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


def get_cb_historical_from_ttjj(code):
    if code.startswith("SH") or code.startswith("SZ"):
        code = code[2:]
    params = {
        "type": "RPTA_WEB_KZZ_LS",
        "sty": "ALL",
        "source": "WEB",
        "p": "1",
        "ps": "8000",
        "st": "date",
        "sr": "1",
        "filter": "(zcode={code})".format(code=code),
    }
    url = "http://datacenter.eastmoney.com/api/data/get"
    data = []
    r = rget_json(url, params=params)
    data.extend(r["result"]["data"])
    if int(r["result"]["pages"]) > 1:
        for i in range(2, int(r["result"]["pages"]) + 1):
            params["p"] = str(i)
            r = rget_json(url, params=params)
            data.extend(r["result"]["data"])
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["DATE"])
    df["bond_value"] = df["PUREBONDVALUE"]
    df["swap_value"] = df["SWAPVALUE"]
    df["close"] = df["FCLOSE"]
    return df[["date", "close", "bond_value", "swap_value"]]


## 常见标的合集列表，便于共同分析, 欢迎贡献:)

# 战略配售封基
zlps = ["SZ160142", "SZ161131", "SZ161728", "SH501186", "SH501188", "SH501189"]


## some small tools and calculators

## the following are truning into xalpha officially supported pipelines soon.


def BlackScholes(S, K, t, v, r=0.02, CallPutFlag="C"):
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


def cb_bond_value(issue_date, rlist, rate=0.03, date=None, tax=1.0):
    """
    可转债债券价值计算器

    :param issue_date: str. 发行日期
    :param rlist: List[float], 每年度的利息百分点，比如 0.4,0.6等，最后加上最后返回的值（不含最后一年利息），比如 104
    :param rate:  float，现金流折算利率，应取同久期同信用等级的企业债利率，参考 https://yield.chinabond.com.cn/
    :param date: 默认今天，计算债券价值基于的时间
    :param tax: float，税率，1.0 表示不算税后，0.8 为计算税后利息，一般不需要设置成0.8，因为区别不大
    :return:
    """

    if rlist[-1] < 100:
        logger.warning(
            "the format of rlist must contain the final return more than 100 without interest of that year"
        )
    issue_date = issue_date.replace("-", "").replace("/", "")
    issue_date_obj = dt.datetime.strptime(issue_date, "%Y%m%d")
    if date is None:
        date_obj = dt.datetime.today()
    else:
        date = date.replace("-", "").replace("/", "")
        date_obj = dt.datetime.strptime(date, "%Y%m%d")
    cf = [(date_obj, 0)]
    passed = (date_obj - issue_date_obj).days // 365
    for i, r in enumerate(rlist[:-1]):
        if i >= passed:
            cf.append((issue_date_obj + dt.timedelta(days=(i + 1) * 365), r * tax))
    cf.append((issue_date_obj + dt.timedelta(days=(len(rlist) - 1) * 365), rlist[-1]))
    return xnpv(rate, cf)


def cb_ytm(issue_date, rlist, cp, date=None, tax=1.0, guess=0.01):
    """
    可转债到期收益率计算器

    :param issue_date: 发行日期
    :param rlist: 计息及赎回列表
    :param cp: 可转债现价
    :param date: 参考日期
    :param tax: 计税 1 vs 0.8 税后 YTM
    :param guess: YTM 估计初始值
    :return:
    """

    if rlist[-1] < 100:
        logger.warning(
            "the format of rlist must contain the final return more than 100 without interest of that year"
        )
    issue_date = issue_date.replace("-", "").replace("/", "")
    issue_date_obj = dt.datetime.strptime(issue_date, "%Y%m%d")
    if date is None:
        date_obj = dt.datetime.today()
    else:
        date = date.replace("-", "").replace("/", "")
        date_obj = dt.datetime.strptime(date, "%Y%m%d")
    cf = [(date_obj, -cp)]
    passed = (date_obj - issue_date_obj).days // 365
    for i, r in enumerate(rlist[:-1]):
        if i >= passed:
            cf.append((issue_date_obj + dt.timedelta(days=(i + 1) * 365), r * tax))
    # 关于赎回利息计算： https://www.jisilu.cn/?/question/339
    # https://www.jisilu.cn/question/5807
    # 富投网的算法：将最后一年超出100的部分，全部按照20%计税，
    cf.append((issue_date_obj + dt.timedelta(days=(len(rlist) - 1) * 365), rlist[-1]))
    #     print(cf)
    return xirr(cf, guess=guess)


@lru_cache()
def get_bond_rates(rating, date=None):
    """
    获取各评级企业债的不同久期的预期利率

    :param rating: str. eg AAA, AA-, N for 中国国债
    :param date: %Y-%m-%d
    :return:
    """
    rating_uid = {
        "N": "2c9081e50a2f9606010a3068cae70001",
        "AAA": "2c9081e50a2f9606010a309f4af50111",
        "AAA-": "8a8b2ca045e879bf014607ebef677f8e",
        "AA+": "2c908188138b62cd01139a2ee6b51e25",
        "AA": "2c90818812b319130112c279222836c3",
        "AA-": "8a8b2ca045e879bf014607f9982c7fc0",
        "A+": "2c9081e91b55cc84011be40946ca0925",
        "A": "2c9081e91e6a3313011e6d438a58000d",
    }

    def _fetch(date):
        r = rpost(
            "https://yield.chinabond.com.cn/cbweb-mn/yc/searchYc?\
xyzSelect=txy&&workTimes={date}&&dxbj=0&&qxll=0,&&yqqxN=N&&yqqxK=K&&\
ycDefIds={uid}&&wrjxCBFlag=0&&locale=zh_CN".format(
                uid=rating_uid[rating], date=date
            ),
        )
        return r

    if not date:
        date = dt.datetime.today().strftime("%Y-%m-%d")

    r = _fetch(date)
    while len(r.text.strip()) < 20:  # 当天没有数据，非交易日
        date = last_onday(date).strftime("%Y-%m-%d")
        r = _fetch(date)
    l = r.json()[0]["seriesData"]
    l = [t for t in l if t[1]]
    df = pd.DataFrame(l, columns=["year", "rate"])
    return df


class CBCalculator:
    """
    可转债内在价值，简单计算器，期权价值与债券价值估算
    """

    def __init__(
        self, code, bondrate=None, riskfreerate=None, volatility=None, name=None
    ):
        """

        :param code: str. 转债代码，包含 SH 或 SZ 字头
        :param bondrate: Optional[float]. 评估所用的债券折现率，默认使用中证企业债对应信用评级对应久期的利率
        :param riskfreerate: Optioal[float]. 评估期权价值所用的无风险利率，默认使用国债对应久期的年利率。
        :param volatility: Optional[float]. 正股波动性百分点，默认在一个范围浮动加上历史波动率的小幅修正。
        :param name: str. 对于历史回测，可以直接提供 str，免得多次 get_rt 获取 name
        """
        # 应该注意到该模型除了当天外，其他时间估计会利用现在的转股价，对于以前下修过转股价的转债历史价值估计有问题

        self.code = code
        self.refbondrate = bondrate
        self.bondrate = self.refbondrate
        self.refriskfreerate = riskfreerate
        self.riskfreerate = self.refriskfreerate
        self.refvolatility = volatility
        self.volatility = self.refvolatility
        self.name = name

        r = rget("https://www.jisilu.cn/data/convert_bond_detail/" + code[2:])
        r.encoding = "utf-8"
        b = BeautifulSoup(r.text, "lxml")
        self.rlist = [
            float(re.search(r"[\D]*([\d]*.[\d]*)\%", s).group(1))
            for s in b.select("td[id=cpn_desc]")[0].string.split("、")
        ]
        self.rlist.append(float(b.select("td[id=redeem_price]")[0].string))
        self.rlist[-1] -= self.rlist[-2]  # 最后一年不含息返多少
        self.scode = (
            b.select("td[class=jisilu_nav]")[0].contents[1].string.split("-")[1].strip()
        )
        self.scode = ttjjcode(self.scode)  # 标准化股票代码
        self.zgj = float(b.select("td[id=convert_price]")[0].string)  # 转股价
        self.rating = b.select("td[id=rating_cd]")[0].string
        self.enddate = b.select("td[id=maturity_dt]")[0].string

    def process_byday(self, date):
        if not date:
            self.date_obj = dt.datetime.today()
        else:
            self.date_obj = dt.datetime.strptime(
                date.replace("-", "").replace("/", ""), "%Y%m%d"
            )
        if not date:
            rt = get_rt(self.code)
            self.name = rt["name"]
            self.cbp = rt["current"]  # 转债价
            self.stockp = get_rt(self.scode)["current"]  # 股票价
        else:
            try:
                if not self.name:
                    rt = get_rt(self.code)
                    self.name = rt["name"]
            except:
                self.name = "unknown"
            df = xu.get_daily(self.code, prev=100, end=self.date_obj.strftime("%Y%m%d"))
            self.cbp = df.iloc[-1]["close"]
            df = xu.get_daily(
                self.scode, prev=100, end=self.date_obj.strftime("%Y%m%d")
            )
            self.stockp = df.iloc[-1]["close"]

        df = xu.get_daily(self.scode, prev=360, end=self.date_obj.strftime("%Y%m%d"))
        self.history_volatility = np.std(
            np.log(df["close"] / df.shift(1)["close"])
        ) * np.sqrt(244)
        if not self.refvolatility:
            self.volatility = 0.17
            if self.rating in ["A", "A+", "AA-"]:
                self.volatility = 0.19
            elif self.rating in ["AA"]:
                self.volatility = 0.18
            if self.history_volatility < 0.25:
                self.volatility -= 0.01
            elif self.history_volatility > 0.65:
                self.volatility += 0.02
            elif self.history_volatility > 0.45:
                self.volatility += 0.01
        self.years = len(self.rlist) - 1
        syear = int(self.enddate.split("-")[0]) - self.years
        self.issuedate = str(syear) + self.enddate[4:]
        self.days = (
            dt.datetime.strptime(self.enddate, "%Y-%m-%d") - self.date_obj
        ).days
        if not self.refbondrate:
            ratestable = get_bond_rates(self.rating, self.date_obj.strftime("%Y-%m-%d"))
            if self.rating in ["A", "A+", "AA-"]:
                ## AA 到 AA- 似乎是利率跳高的一个坎
                cutoff = 2
            else:
                cutoff = 4
            if self.days / 365 > cutoff:
                # 过长久期的到期收益率，容易造成估值偏离，虽然理论上是对的
                # 考虑到国内可转债市场信用风险较低，不应过分低估低信用债的债券价值
                self.bondrate = (
                    ratestable[ratestable["year"] <= cutoff].iloc[-1]["rate"] / 100
                )
            else:
                self.bondrate = (
                    ratestable[ratestable["year"] >= self.days / 365].iloc[0]["rate"]
                    / 100
                )
        if not self.refriskfreerate:
            ratestable = get_bond_rates("N", self.date_obj.strftime("%Y-%m-%d"))
            if self.days / 365 > 5:
                self.riskfreerate = (
                    ratestable[ratestable["year"] <= 5].iloc[-1]["rate"] / 100
                )
            else:
                self.riskfreerate = (
                    ratestable[ratestable["year"] >= self.days / 365].iloc[0]["rate"]
                    / 100
                )

    def analyse(self, date=None):
        self.process_byday(date=date)
        d = {
            "stockcode": self.scode,
            "cbcode": self.code,
            "name": self.name,
            "enddate": self.enddate,
            "interest": self.rlist,
            "zgj": self.zgj,
            "stockprice": self.stockp,
            "cbprice": self.cbp,
            "rating": self.rating,
            "bondrate": self.bondrate,
            "predicted_volatility": self.volatility,
            "historical_valatility": self.history_volatility,
            "riskfreerate": self.riskfreerate,
            "years": self.days / 365,
            "issuedate": self.issuedate,
            "date": self.date_obj.strftime("%Y-%m-%d"),
        }
        d["bond_value"] = cb_bond_value(self.issuedate, self.rlist, self.bondrate)
        d["ytm_wo_tax"] = cb_ytm(self.issuedate, self.rlist, self.cbp)
        d["ytm_wi_tax"] = cb_ytm(self.issuedate, self.rlist, self.cbp, tax=0.8)
        d["option_value"] = (
            BlackScholes(
                self.stockp,
                self.zgj,
                self.days / 365,
                self.volatility,
                self.riskfreerate,
                CallPutFlag="C",
            )
            * 100
            / self.zgj
        )
        # 经验上看，下修强赎回售及美式期权行为等其他带来的期权价值大约有1到4元的增益：
        # 以0.015 为无风险利率和 0.15-0.18 为波动率估计范围的情形下
        # 实在没有必要为了这几块钱上复杂工具估值，因为无风险利率几十个bp的改变，就足以导致更大的波动，看个热闹就行了
        # 可转债估值只能是模糊的正确
        d["tot_value"] = d["bond_value"] + d["option_value"]
        d["premium"] = (self.cbp / d["tot_value"] - 1) * 100
        return d
