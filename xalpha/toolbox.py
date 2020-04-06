# -*- coding: utf-8 -*-
"""
modules for Object oriented toolbox which wrappers get_daily and some more
"""

import sys
import datetime as dt
import numpy as np
import pandas as pd
from collections import deque
from functools import wraps, lru_cache
import logging

from xalpha.cons import (
    opendate,
    yesterday,
    next_onday,
    last_onday,
    scale_dict,
    tz_bj,
    holidays,
)
from xalpha.universal import (
    get_rt,
    get_bar,
    _convert_code,
    _inverse_convert_code,
    get_newest_netvalue,
    fetch_backend,
    save_backend,
)
import xalpha.universal as xu  ## 为了 set_backend 可以动态改变此模块的 get_daily
from xalpha.exceptions import ParserFailure, DateMismatch, NonAccurate

thismodule = sys.modules[__name__]

logger = logging.getLogger(__name__)


def _set_holdings(module):
    for name in [
        "no_trading_days",
        "holdings",
        "currency_info",
        "market_info",
        "futures_info",
        "alt_info",
        "gap_info",
    ]:
        setattr(thismodule, name, getattr(module, name, {}))


def set_holdings(module=None):
    """
    导入外部 holdings.py 数据文件用来预测基金净值

    :param module: mod. import holdings
    :return: None.
    """
    if not module:
        try:
            from xalpha import holdings

            _set_holdings(holdings)
            print("holdings.py is found and loaded within xalpha dir")
        except ImportError:
            # print("no holdings.py is found") # may cause confusing for general users
            from xalpha import cons

            _set_holdings(cons)
    else:
        _set_holdings(module)
        print("external holdings.py is loaded")


set_holdings()


class PEBHistory:
    """
    对于指数历史 PE PB 的封装类
    """

    indexs = {
        "000016.XSHG": ("上证50", "2012-01-01"),
        "000300.XSHG": ("沪深300", "2012-01-01"),
        "000905.XSHG": ("中证500", "2012-01-01"),
        "000922.XSHG": ("中证红利", "2012-01-01"),
        "399006.XSHE": ("创业板指", "2012-01-01"),
        "000992.XSHG": ("全指金融", "2012-01-01"),
        "000991.XSHG": ("全指医药", "2012-01-01"),
        "399932.XSHE": ("中证消费", "2012-01-01"),
        "000831.XSHG": ("500低波", "2013-01-01"),
        "000827.XSHG": ("中证环保", "2013-01-01"),
        "000978.XSHG": ("医药100", "2012-01-01"),
        "399324.XSHE": ("深证红利", "2012-01-01"),
        "399971.XSHE": ("中证传媒", "2014-07-01"),
        "000807.XSHG": ("食品饮料", "2013-01-01"),
        "000931.XSHG": ("中证可选", "2012-01-01"),
        "399812.XSHE": ("养老产业", "2016-01-01"),
        "000852.XSHG": ("中证1000", "2015-01-01"),
    }

    # 聚宽数据源支持的指数列表： https://www.joinquant.com/indexData

    def __init__(self, code, start=None, end=None):
        """

        :param code: str. 形式可以是 399971.XSHE 或者 SH000931
        :param start: Optional[str]. %Y-%m-%d, 估值历史计算的起始日。
        :param end: Dont use, only for debug
        """
        yesterday_str = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
        if len(code.split(".")) == 2:
            self.code = code
            self.scode = _convert_code(code)
        else:
            self.scode = code
            self.code = _inverse_convert_code(self.scode)
        if self.code in self.indexs:
            self.name = self.indexs[self.code][0]
            if not start:
                start = self.indexs[self.code][1]
        else:
            try:
                self.name = get_rt(self.scode)["name"]
            except:
                self.name = self.scode
            if not start:
                start = "2012-01-01"  # 可能会出问题，对应指数还未有数据
        self.start = start
        if not end:
            end = yesterday_str
        self.df = xu.get_daily("peb-" + self.scode, start=self.start, end=end)
        self.ratio = None
        self.title = "指数"
        self._gen_percentile()

    def _gen_percentile(self):
        self.pep = [
            round(i, 3) for i in np.nanpercentile(self.df.pe, np.arange(0, 110, 10))
        ]
        self.pbp = [
            round(i, 3) for i in np.nanpercentile(self.df.pb, np.arange(0, 110, 10))
        ]

    def percentile(self):
        """
        打印 PE PB 的历史十分位对应值

        :return:
        """
        print("PE 历史分位:\n")
        print(*zip(np.arange(0, 110, 10), self.pep), sep="\n")
        print("\nPB 历史分位:\n")
        print(*zip(np.arange(0, 110, 10), self.pbp), sep="\n")

    def v(self, y="pe"):
        """
        pe 或 pb 历史可视化

        :param y: Optional[str]. "pe" (defualt) or "pb"
        :return:
        """
        return self.df.plot(x="date", y=y)

    def fluctuation(self):
        if not self.ratio:
            d = self.df.iloc[-1]["date"]
            oprice = xu.get_daily(
                code=self.scode, end=d.strftime("%Y%m%d"), prev=20
            ).iloc[-1]["close"]
            nprice = get_rt(self.scode)["current"]
            self.ratio = nprice / oprice
        return self.ratio

    def current(self, y="pe"):
        """
        返回实时的 pe 或 pb 绝对值估计。

        :param y: Optional[str]. "pe" (defualt) or "pb"
        :return: float.
        """
        return round(self.df.iloc[-1][y] * self.fluctuation(), 3)

    def current_percentile(self, y="pe"):
        """
        返回实时的 pe 或 pb 历史百分位估计

        :param y: Optional[str]. "pe" (defualt) or "pb"
        :return: float.
        """
        df = self.df
        d = len(df)
        u = len(df[df[y] < self.current(y)])
        return round(u / d * 100, 2)

    def summary(self):
        """
        打印现在估值的全部分析信息。

        :return:
        """
        print("%s%s估值情况\n" % (self.title, self.name))
        if dt.datetime.strptime(self.start, "%Y-%m-%d") > dt.datetime(2015, 1, 1):
            print("(历史数据较少，仅供参考)\n")
        #         self.percentile()
        print(
            "现在 PE 绝对值 %s, 相对分位 %s%%，距离最低点 %s %%\n"
            % (
                self.current("pe"),
                self.current_percentile("pe"),
                max(
                    round(
                        (self.current("pe") - self.pep[0]) / self.current("pe") * 100, 1
                    ),
                    0,
                ),
            )
        )
        print(
            "现在 PB 绝对值 %s, 相对分位 %s%%，距离最低点 %s %%\n"
            % (
                self.current("pb"),
                self.current_percentile("pb"),
                max(
                    round(
                        (self.current("pb") - self.pbp[0]) / self.current("pb") * 100, 1
                    ),
                    0,
                ),
            )
        )


class SWPEBHistory(PEBHistory):
    """
    申万一级行业指数列表：
    https://www.hysec.com/hyzq/hy/detail/detail.jsp?menu=4&classid=00000003001200130002&firClassid=000300120013&twoClassid=0003001200130002&threeClassid=0003001200130002&infoId=3046547
    二三级行业指数也支持
    """

    index1 = [
        "801740",
        "801020",
        "801110",
        "801200",
        "801160",
        "801010",
        "801120",
        "801230",
        "801750",
        "801050",
        "801890",
        "801170",
        "801710",
        "801130",
        "801180",
        "801760",
        "801040",
        "801780",
        "801880",
        "801140",
        "801720",
        "801080",
        "801790",
        "801030",
        "801730",
        "801210",
        "801770",
        "801150",
    ]

    def __init__(self, code, start=None, end=None):
        """

        :param code: 801180 申万行业指数
        :param start:
        :param end:
        """
        self.code = code
        self.scode = code
        if not end:
            end = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
        if not start:
            start = "2012-01-01"
        self.start = start
        self.df = xu.get_daily("sw-" + code, start=start, end=end)
        self.name = self.df.iloc[0]["name"]
        self.ratio = 1
        self.title = "申万行业指数"
        self._gen_percentile()


class Compare:
    """
    将不同金融产品同起点归一化比较
    """

    def __init__(self, *codes, start="20200101", end=yesterday(), col="close"):
        """

        :param codes: Union[str, tuple], 格式与 :func:`xalpha.universal.get_daily` 相同，若需要汇率转换，需要用 tuple，第二个元素形如 "USD"
        :param start: %Y%m%d
        :param end: %Y%m%d, default yesterday
        """
        totdf = pd.DataFrame()
        codelist = []
        for c in codes:
            if isinstance(c, tuple):
                code = c[0]
                currency = c[1]
            else:
                code = c
                currency = "CNY"  # 标的不做汇率调整
            codelist.append(code)
            df = xu.get_daily(code, start=start, end=end)
            df = df[df.date.isin(opendate)]
            currency_code = _get_currency_code(currency)
            if currency_code:
                cdf = xu.get_daily(currency_code, start=start, end=end)
                cdf = cdf[cdf["date"].isin(opendate)]
                df = df.merge(right=cdf, on="date", suffixes=("_x", "_y"))
                df[col] = df[col + "_x"] * df[col + "_y"]
            df[code] = df[col] / df.iloc[0][col]
            df = df.reset_index()
            df = df[["date", code]]
            if "date" not in totdf.columns:
                totdf = df
            else:
                totdf = totdf.merge(on="date", right=df)
        self.totdf = totdf
        self.codes = codelist

    def v(self):
        """
        显示日线可视化

        :return:
        """
        return self.totdf.plot(x="date", y=self.codes)

    def corr(self):
        """
        打印相关系数矩阵

        :return: pd.DataFrame
        """
        return self.totdf.iloc[:, 1:].pct_change().corr()


#########################
# netvalue prediction   #
#########################


@lru_cache(maxsize=512)
def get_currency(code):
    """
    通过代码获取计价货币的函数

    :param code:
    :return:
    """
    # 强制需要自带 cache，否则在回测 table 是，info 里没有的代码将很灾难。。。
    # only works for HKD JPY USD GBP CNY EUR, not very general when data source gets diverse more
    try:
        if code in currency_info:
            return currency_info[code]
        elif (code.startswith("F") or code.startswith("M")) and code[1:].isdigit():
            return "CNY"
        currency = get_rt(code)["currency"]
        if currency is None:
            currency = "CNY"
        elif currency == "JPY":
            currency = "100JPY"
    except (TypeError, AttributeError, ValueError):
        if code.startswith("FT-") and len(code.split(":")) > 2:
            currency = code.split(":")[-1]
        else:
            currency = "CNY"
    return currency


def _get_currency_code(c):
    if c == "CNY":
        return  # None
    if c == "JPY":
        return "100JPY/CNY"
    zjjl = [
        "USD",
        "EUR",
        "100JPY",
        "HKD",
        "GBP",
        "AUD",
        "NZD",
        "SGD",
        "CHF",
        "CAD",
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
    if c in zjjl:
        return c + "/CNY"
    return "currencies/" + c.lower() + "-cny"


@lru_cache(maxsize=512)
def get_currency_code(code):
    c = get_currency(code)
    return _get_currency_code(c)


@lru_cache(maxsize=512)
def get_market(code):
    """
    非常粗糙的通过代码获取交易市场的函数

    :param code:
    :return:
    """
    trans = {
        "USD": "US",
        "GBP": "UK",
        "HKD": "HK",
        "CNY": "CN",
        "CHF": "CH",
        "JPY": "JP",
        "EUR": "DE",
        "AUD": "AU",
        "INR": "IN",
        "SGD": "SG",
    }
    try:
        if code in market_info:
            return market_info[code]
        elif code.startswith("CNY/") or code.endswith("/CNY"):
            return "CM"  # china money 中间价市场标记
        market = get_rt(code)["market"]
        if market is None:
            market = get_currency(code)
            market = trans.get(market, market)
    except (TypeError, AttributeError, ValueError, IndexError):
        market = "CN"
    return market


@lru_cache(maxsize=512)
def get_alt(code):
    """
    抓取失败后寻找替代对等标的

    :param code:
    :return:
    """
    if code in alt_info:
        return alt_info[code]
    elif len(code[1:].split("/")) == 2:
        return "INA-" + code
    else:
        return None


def _is_on(code, date):
    df = xu.get_daily(code, prev=20, end=date)
    if len(df[df["date"] == date]) == 0:
        return False
    return True


def is_on(date, market="CN", no_trading_days=None):
    """
    粗略鉴定 date 日是否是指定 market 的开市日，对于当日鉴定，仍有数据未及时更新的风险。也存在历史数据被 investing 补全的风险。

    :param date:
    :param market: str. CN, JP, HK, US, UK, CH, HK, DE
    :return: bool.
    """

    date_obj = dt.datetime.strptime(date.replace("-", "").replace("/", ""), "%Y%m%d")
    if date_obj.weekday() in [5, 6]:  # 周末休市
        # 注意部分中东市场周日开市，暂时涉及不到
        return False
    date_dash = date_obj.strftime("%Y-%m-%d")
    if no_trading_days:
        if date_dash in no_trading_days.get(market, []):
            return False
    if date_dash in holidays.get(market, []):
        return False
    logger.warning(
        "determine whether %s is holiday in %s market, but may be wrong, be careful!"
        % (date_dash, market)
    )
    if market in ["CN", "CHN", "CNY", "RMB", "CHINA", "CM"]:  # 国内节假日不更新中间价
        return date_dash in opendate
    elif market in ["JP", "JAPAN", "JPY", "100JPY"]:
        code = "indices/japan-ni225"
    elif market in ["US", "NY", "USD", "NASDAQ"]:
        code = "indices/us-spx-500"
    elif market in ["GBP", "UK", "GB"]:
        code = "indices/uk-100"
    elif market in ["GER", "EUR", "DE"]:  # 是否可以代表欧洲待考量, 还要警惕欧洲市场的美元计价标的
        code = "indices/germany-30"
    elif market in ["CHF", "SWI", "CH"]:
        code = "indices/switzerland-20"
    elif market in ["HK"]:
        code = "indices/hang-sen-40"
    else:
        logger.warning(
            "unknown oversea market %s, assuming %s is not a holiday"
            % (market, date_dash)
        )
        return True
    return _is_on(code, date)


def daily_increment(code, date, lastday=None, _check=False):
    """
    单一标的 date 日（若 date 日无数据则取之前的最晚有数据日，但该日必须大于 _check 对应的日期）较上一日或 lastday 的倍数，
    lastday 支持不完整，且不能离 date 太远

    :param code:
    :param date:
    :param lastday: 如果用默认 None，则表示和前一日的涨跌
    :param _check: 数据必须已更新到 date 日，除非之前每天都是节假日
    :return:
    """
    try:
        tds = xu.get_daily(code=code, end=date, prev=30)
    except Exception as e:  # 只能笼统 catch 了，因为抓取失败的异常是什么都能遇到。。。
        code = get_alt(code)
        if code:
            tds = xu.get_daily(code=code, end=date, prev=30)
        else:
            raise e
    tds = tds[tds["date"] <= date]
    if _check:
        date = date.replace("-", "").replace("/", "")
        date_obj = dt.datetime.strptime(date, "%Y%m%d")
        while tds.iloc[-1]["date"] < date_obj:
            # in case data is not up to date
            # 但是存在日本市场休市时间不一致的情况，估计美股也存在
            if not is_on(
                date_obj.strftime("%Y%m%d"),
                get_market(code),
                no_trading_days=no_trading_days,
            ) or (date_obj.strftime("%Y-%m-%d") in gap_info.get(code, [])):
                print("%s is closed on %s" % (code, date))
                if not lastday:
                    return 1  # 当日没有涨跌，这里暂时为考虑 _check 和 lastday 相同的的情形
                date_obj -= dt.timedelta(days=1)
            else:
                raise DateMismatch(
                    code,
                    reason="%s has no data newer than %s"
                    % (code, date_obj.strftime("%Y-%m-%d")),
                )
    if not lastday:
        ratio = tds.iloc[-1]["close"] / tds.iloc[-2]["close"]
    else:
        tds2 = tds[tds["date"] <= lastday]
        # 未考虑连 lastday 的数据数据源都没更新的情形，这种可能极小
        ratio = tds.iloc[-1]["close"] / tds2.iloc[-1]["close"]
    return ratio


def _smooth_pos(r, e, o):
    """
    单日仓位估计的平滑函数

    :param r: 实际涨幅
    :param e: 满仓估计涨幅
    :param o: 昨日仓位估计
    :return:
    """
    pos = r / e
    if pos <= 0:
        return o
    if pos > 1:
        pos = 1
    elif pos < 0.5:
        pos = pos ** 0.6

    if abs(r) < 0.6:
        pos = (pos + (3 - 5 * abs(r)) * o) / (4 - 5 * abs(r))

    return pos


def error_catcher(f):
    """
    装饰器，透明捕获 DateMismatch

    :param f:
    :return:
    """

    @wraps(f)
    def wrapper(*args, **kws):
        try:
            return f(*args, **kws)
        except DateMismatch as e:
            code = args[0]
            error_msg = e.reason
            error_msg += ", therefore %s cannot predict correctly" % code
            raise NonAccurate(code=code, reason=error_msg)

    return wrapper


def evaluate_fluctuation(hdict, date, lastday=None, _check=None):
    """
    分析资产组合 hdict 的涨跌幅，全部兑换成人民币考虑

    :param hdict:
    :param date:
    :param lastday:
    :param _check:
    :return:
    """
    price = 0
    tot = 0

    for fundid, percent in hdict.items():
        ratio = daily_increment(fundid, date, lastday, _check)
        exchange = 1
        currency = get_currency_code(fundid)
        if currency:
            exchange = daily_increment(currency, date, lastday, _check)
        price += ratio * percent / 100 * exchange
        tot += percent
    remain = 100 - tot
    price += remain / 100
    return (price - 1) * 100


class RTPredict:
    """
    场内 ETF LOF 实时溢价，非 QDII 类
    """

    def __init__(self, code, t0dict=None):
        """

        :param code:
        :param t0dict:
        """
        self.code = code
        self.fcode = "F" + code[2:]
        if not t0dict:
            t0dict = holdings.get(code[2:], None)
        if not t0dict:
            raise ValueError("Please provide t0dict for prediction")
        if isinstance(t0dict, str):
            t0dict = {t0dict: 100}
        self.t0dict = t0dict
        self.t1value_cache = None
        self.now = dt.datetime.now(tz=tz_bj).replace(tzinfo=None)
        self.today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_t1(self, return_date=True):
        """
        获取昨日基金净值

        :return:
        """
        if not self.t1value_cache:
            last_value, last_date = get_newest_netvalue(self.fcode)
            self.t1value_cache = (last_value, last_date)
        if return_date:
            return self.t1value_cache
        else:
            return self.t1value_cache[0]

    def get_t0(self, return_date=True, percent=False):
        last_value, last_date = self.get_t1()
        last_date_obj = dt.datetime.strptime(last_date, "%Y-%m-%d")
        cday = last_onday(self.today)
        while last_date_obj < cday:  # 昨天净值数据还没更新
            # 是否存在部分部分基金可能有 gap？
            if cday.strftime("%Y-%m-%d") not in gap_info[self.fcode]:
                self.t1_type = "昨日未出"
                raise DateMismatch(
                    self.code,
                    reason="%s netvalue has not been updated to yesterday" % self.code,
                )
            else:
                cday = last_onday(cday)
            # 经过这个没报错，就表示数据源是最新的
        if last_date_obj >= self.today:  # 今天数据已出，不需要再预测了
            print(
                "no need to predict net value since it has been out for %s" % self.code
            )
            self.t1_type = "今日已出"
            if not return_date:
                return last_value
            else:
                return last_value, last_date
        t = 0
        n = 0
        today_str = self.today.strftime("%Y%m%d")
        for k, v in self.t0dict.items():
            w = v
            t += w
            r = get_rt(k)
            # k should support get_rt, investing pid doesn't support this!
            if percent:
                c = w / 100 * (1 + r["percent"] / 100)  # 直接取标的当日涨跌幅
            else:
                df = xu.get_daily(k)
                basev = df[df["date"] < self.today].iloc[-1]["close"]
                c = w / 100 * r["current"] / basev
            currency_code = get_currency_code(k)
            if currency_code:
                c = c * daily_increment(currency_code, today_str)
            n += c
        n += (100 - t) / 100
        t0value = n * last_value
        self.t0_delta = n
        if not return_date:
            return t0value
        else:
            return t0value, self.today.strftime("%Y-%m-%d")

    def get_t0_rate(self, percent=False, return_date=True):
        iopv = self.get_t0(percent=False, return_date=False)
        rtv = get_rt(self.code)["current"]
        r = (rtv / iopv - 1) * 100
        if return_date:
            return r, self.today.strftime("%Y-%m-%d")
        else:
            return r


class QDIIPredict:
    """
    T+2 确认份额的 QDII 型基金净值预测类
    
    .. warning::

        由于该类与现实时间的强烈耦合和激进的缓存利用，该类的对象不能"过夜"使用，每天需声明新的对象

    """

    def __init__(
        self, code, t1dict=None, t0dict=None, positions=False, fetch=False, save=False
    ):
        """

        :param code: str, 场内基金代码，eg SH501018
        :param t1dict: Dict[str, float]. 用来预测 T-1 净值的基金组合持仓，若为空自动去 holdings 中寻找。
        :param t0ict: Dict[str, float]. 用来预测 T 实时净值的基金组合持仓，若为空自动去 holdings 中寻找。
        :param positions: bool. 仓位是否浮动，默认固定仓位。
        :param fetch: bool, default True. 优先从 backend fetch t1。
        :param save: bool, default True. 将 t1 缓存到 backend。
        """
        self.code = code
        self.fcode = "F" + code[2:]
        self.fetch = fetch
        self.save = save

        if not t1dict:
            self.t1dict = holdings.get(code[2:], None)
            if not self.t1dict:
                raise ValueError("Please provide t1dict for prediction")
        else:
            self.t1dict = t1dict
        if not t0dict:
            self.t0dict = holdings.get(code[2:] + "rt", None)
        else:
            self.t0dict = t0dict
        self.position_cache = {}
        self.t1value_cache = {}
        self.t2value_cache = None
        # t0 实时净值自然不 cache
        self.positions = positions
        self.position_zero = sum([v for _, v in self.t1dict.items()])
        self.now = dt.datetime.now(tz=tz_bj).replace(tzinfo=None)
        self.today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.t1_type = "未计算"
        self.bar_cache = {}
        self.t0_delta = None
        self.t1_delta = None
        # 不建议直接使用以上两者看变化量，在手动 set 后，以上两者可能继续为 None
        if fetch:
            df = fetch_backend("t1-" + code)
            if df is not None:
                df["date"] = pd.to_datetime(df["date"])
                for i, r in df.iterrows():
                    self.set_t1(float(r["t1"]), r["date"].strftime("%Y-%m-%d"))

    def set_t1(self, value, date=None):
        """
        设定 T-1 的基金净值，有时我们只想计算实时净值，这就不需要重复计算 t1，可以先行设定

        :param value:
        :param date:
        :return:
        """
        if date is None:
            yesterday = last_onday(self.today)
            datekey = yesterday.strftime("%Y%m%d")
        else:
            datekey = date.replace("/", "").replace("-", "")
        if datekey in self.t1value_cache:
            logger.debug("t-1 value already exists, rewriting...")
        self.t1value_cache[datekey] = value
        self.t1_type = "已计算"

    def set_t2(self, value, date=None):
        """
        手动设定 t2 净值

        :param value:
        :return:
        """
        if not date:
            date = last_onday(last_onday(self.today)).strftime("%Y-%m-%d")
        self.t2value_cache = (value, date)

    def get_t2(self, return_date=True):
        """
        返回最新的已公布基金净值，注意这里严格按照最新公布，不一定是前两个交易日，可以更新，但更老会报错 DateMismatch

        :param return_date:
        :return: if return_date is True, tuple (value, %Y-%m-%d)
        """
        if not self.t2value_cache:
            last_value, last_date = get_newest_netvalue(self.fcode)
            self.t2value_cache = (last_value, last_date)
        if return_date:
            return self.t2value_cache
        else:
            return self.t2value_cache[0]

    @error_catcher
    def get_t1(self, date=None, return_date=True):
        """
        预测 date 日的净值，基于 date-1 日的净值和 date 日的外盘数据，数据自动缓存，不会重复计算

        :param date: str. %Y-%m-%d. 注意若是 date 日为昨天，即今日预测昨日的净值，date 取默认值 None。
        :param return_date: bool, default True. return tuple, the second one is date in the format %Y%m%d
        :return: float, (str).
        :raises NonAccurate: 由于外盘数据还未及时更新，而 raise，可在调用程序中用 except 捕获再处理。
        """
        if date is None:
            yesterday = last_onday(self.today)
            datekey = yesterday.strftime("%Y%m%d")
        else:
            datekey = date.replace("/", "").replace("-", "")
        if datekey not in self.t1value_cache:
            logger.debug("no cache for t1 value, computing from beginning")
            if self.positions:
                current_pos = self.get_position(datekey, return_date=False)
                hdict = scale_dict(self.t1dict.copy(), aim=current_pos * 100)
            else:
                hdict = self.t1dict.copy()

            if date is None:  # 此时预测上个交易日净值
                yesterday_str = datekey
                last_value, last_date = self.get_t2()
                last_date_obj = dt.datetime.strptime(last_date, "%Y-%m-%d")
                cday = last_onday(last_onday(self.today))
                while last_date_obj < cday:  # 前天净值数据还没更新
                    # 是否存在部分 QDII 在 A 股交易日，美股休市日不更新净值的情形？
                    if (
                        cday.strftime("%Y-%m-%d") not in gap_info[self.fcode]
                    ) and is_on(cday, "US", no_trading_days):
                        # 这里检查比较宽松，只要当天美股休市，就可以认为确实基金数据不存在而非未更新
                        self.t1_type = "前日未出"
                        raise DateMismatch(
                            self.code,
                            reason="%s netvalue has not been updated to the day before yesterday"
                            % self.code,
                        )
                    else:
                        cday = last_onday(cday)
                    # 经过这个没报错，就表示数据源是最新的
                if last_date_obj >= last_onday(self.today):  # 昨天数据已出，不需要再预测了
                    print(
                        "no need to predict t-1 value since it has been out for %s"
                        % self.code
                    )
                    self.t1_type = "昨日已出"
                    self.t1value_cache = {last_date.replace("-", ""): last_value}
                    if not return_date:
                        return last_value
                    else:
                        return last_value, last_date
            else:
                yesterday_str = datekey
                fund_price = xu.get_daily(self.fcode)  # 获取国内基金净值
                fund_last = fund_price[fund_price["date"] < date].iloc[-1]
                # 注意实时更新应用 date=None 传入，否则此处无法保证此数据是前天的而不是大前天的，因为没做校验
                # 事实上这里计算的预测是针对 date 之前的最晚数据和之前一日的预测
                last_value = fund_last["close"]
                last_date = fund_last["date"].strftime("%Y-%m-%d")
            self.t1_delta = (
                1
                + evaluate_fluctuation(
                    hdict, yesterday_str, lastday=last_date, _check=True
                )
                / 100
            )
            net = last_value * self.t1_delta
            self.t1value_cache[datekey] = net
            self.t1_type = "已计算"
            if self.save:
                df = pd.DataFrame(
                    {
                        "date": [datekey[:4] + "-" + datekey[4:6] + "-" + datekey[6:8]],
                        "t1": [net],
                    }
                )
                save_backend("t1-" + self.code, df)
        if not return_date:
            return self.t1value_cache[datekey]
        else:
            return (
                self.t1value_cache[datekey],
                datekey[:4] + "-" + datekey[4:6] + "-" + datekey[6:8],
            )

    def get_t1_rate(self, date=None, return_date=True):
        t1v, d = self.get_t1(date=date, return_date=True)
        cp = get_rt(self.code)["current"]
        r = (cp / t1v - 1) * 100
        if return_date:
            return r, d
        else:
            return r

    def get_t0_rate(self, percent=False, return_date=True):
        t0v, d = self.get_t0(percent=percent, return_date=True)
        cp = get_rt(self.code)["current"]
        r = (cp / t0v - 1) * 100
        if return_date:
            return r, d
        else:
            return r

    def _base_value(self, code, shift):
        if not shift:
            funddf = xu.get_daily(code)  ## 获取股指现货日线
            return funddf[funddf["date"] < self.today.strftime("%Y-%m-%d")].iloc[-1][
                "close"
            ]  # 日期是按当地时间
        # TODO: check it is indeed date of last_on(today)
        else:
            if code not in self.bar_cache:
                funddf = get_bar(code, prev=48, interval="3600")  ## 获取小时线
                if self.now.hour > 6:  # 昨日美国市场收盘才正常，才缓存参考小时线
                    self.bar_cache[code] = funddf
            else:
                funddf = self.bar_cache[code]
            return funddf[
                funddf["date"] <= self.today + dt.timedelta(hours=shift)
            ].iloc[-1][
                "close"
            ]  # 时间是按北京时间, 小时线只能手动缓存，日线不需要是因为自带透明缓存器

    def get_t0(self, percent=False, return_date=True):
        """
        获取当日实时净值估计, 该接口每日凌晨到美股收盘（早晨），不保证自洽和可用

        :param percent: bool， default False。现在有两种实时的预测处理逻辑。若 percent 是 True，则将 t0dict 的
            每个持仓标的的今日涨跌幅进行估算，若为 False，则将标的现价和标的对应指数昨日收盘价的比例作为涨跌幅估算。不推荐使用 percent=True.
        :param return_date: bool, default True. return tuple, the second one is date in the format %Y%m%d
        :return: float
        """
        if not self.t0dict:
            raise ValueError("Please provide t0dict for prediction")
        t1value = self.get_t1(date=None, return_date=False)
        t = 0
        n = 0
        today_str = self.today.strftime("%Y%m%d")
        for k, v in self.t0dict.items():
            if not isinstance(v, dict):
                v = {"weight": v}
            if len(k.split("~")) > 1 and k.split("~")[-1].isdigit():
                # 为了持仓中可以同标的多次出现的 workaround
                k = k.split("~")[0]
            w = v["weight"]
            shift = v.get("time", None)
            base = v.get("base", None)
            t += w
            r = get_rt(
                k
            )  # k should support get_rt, investing pid doesn't support this!
            if percent:
                c = w / 100 * (1 + r["percent"] / 100)  # 直接取标的当日涨跌幅
            else:
                if k in futures_info and not base:
                    kf = futures_info[k]
                elif not base:
                    kf = k[:-8]  # k + "-futures"
                else:
                    kf = base
                try:
                    basev = self._base_value(kf, shift)
                except Exception as e:
                    kf = get_alt(kf)
                    if not kf:
                        raise e
                    else:
                        basev = self._base_value(kf, shift)
                c = w / 100 * r["current"] / basev
            currency_code = get_currency_code(k)
            if currency_code:
                c = c * daily_increment(currency_code, today_str)
                # TODO: 中间价未更新，但实时数据不检查问题也不大
            n += c
        n += (100 - t) / 100
        t0value = n * t1value
        self.t0_delta = n
        if not return_date:
            return t0value
        else:
            return t0value, self.today.strftime("%Y-%m-%d")

    @error_catcher
    def get_position(self, date=None, refresh=False, return_date=True, **kws):
        """
        基于 date 日之前的净值数据，对 date 预估需要的仓位进行计算。

        :param date: str. %Y-%m-%d
        :param refresh: bool, default False. 若为 True，则刷新缓存，重新计算仓位。
        :param return_date: bool, default True. return tuple, the second one is date in the format %Y%m%d
        :param kws: 一些预估仓位可能的超参。包括 window，预估所需的时间窗口，decay 加权平均的权重衰减，smooth 每日仓位处理的平滑函数。以上参数均可保持默认即可获得较好效果。
        :return: float. 0-100. 100 代表满仓。
        """
        if not date:
            date = last_onday(self.today).strftime("%Y%m%d")
        else:
            date = date.replace("/", "").replace("-", "")
        if date not in self.position_cache or refresh:

            fdict = scale_dict(self.t1dict.copy(), aim=100)
            l = kws.get("window", 4)
            q = kws.get("decay", 0.8)
            s = kws.get("smooth", _smooth_pos)
            d = dt.datetime.strptime(date, "%Y%m%d")
            posl = [sum([v for _, v in self.t1dict.items()]) / 100]
            for _ in range(l):
                d = last_onday(d)
            for _ in range(l - 1):
                d = next_onday(d)
                pred = evaluate_fluctuation(
                    fdict,
                    d.strftime("%Y-%m-%d"),
                    lastday=last_onday(d).strftime("%Y-%m-%d"),
                )
                real = evaluate_fluctuation(
                    {self.fcode: 100},
                    d.strftime("%Y-%m-%d"),
                    lastday=last_onday(d).strftime("%Y-%m-%d"),
                )
                posl.append(s(real, pred, posl[-1]))
            current_pos = sum([q ** i * posl[l - i - 1] for i in range(l)]) / sum(
                [q ** i for i in range(l)]
            )
            self.position_cache[date] = current_pos
        if not return_date:
            return self.position_cache[date]
        else:
            return (
                self.position_cache[date],
                date[:4] + "-" + date[4:6] + "-" + date[6:8],
            )

    def benchmark_test(self, start, end, **kws):
        """
        对该净值预测模型回测

        :param start: str. 起始日期
        :param end: str. 终止日期
        :param kws: 可选仓位估计的超参。
        :return: pd.DataFrame. real 列为真实涨跌幅，est 列为估计涨跌幅，diff 列为两者之差。
        """
        compare_data = {
            "date": [],
        }
        l = kws.get("window", 4)
        q = kws.get("decay", 0.8)
        c = kws.get("pos", self.position_zero)
        s = kws.get("smooth", _smooth_pos)
        real_holdings = {self.fcode: 100}
        full_holdings = scale_dict(self.t1dict.copy(), aim=100)
        compare_data["est"] = []
        compare_data["real"] = []
        compare_data["estpos3"] = []
        compare_data["estpos1"] = []
        fq = deque([c / 100] * l, maxlen=l)
        current_pos = c / 100
        dl = pd.Series(pd.date_range(start=start, end=end))
        dl = dl[dl.isin(opendate)]
        for j, d in enumerate(dl):
            if j == 0:
                continue
            dstr = d.strftime("%Y%m%d")
            lstdstr = dl.iloc[j - 1].strftime("%Y%m%d")
            compare_data["date"].append(d)
            fullestf = evaluate_fluctuation(full_holdings, dstr, lstdstr)
            realf = evaluate_fluctuation(real_holdings, dstr, lstdstr)
            estf = fullestf * current_pos
            compare_data["est"].append(estf)
            compare_data["estpos3"].append(current_pos)
            compare_data["estpos1"].append(fq[-1])
            compare_data["real"].append(realf)
            pos = s(realf, fullestf, fq[-1])
            fq.append(pos)
            fq[0] = c / 100  ## 模拟实际的无状态仓位分析
            if self.positions:
                current_pos = sum([q ** i * fq[l - i - 1] for i in range(l)]) / sum(
                    [q ** i for i in range(l)]
                )
                if current_pos > 1:
                    current_pos = 1

        cpdf = pd.DataFrame(compare_data)
        cpdf["diff"] = cpdf["est"] - cpdf["real"]
        self.cpdf = cpdf
        return cpdf

    def analyse(self):
        """
        打印出回测结果的定量分析。

        :return: None
        """
        print("净值预测回测分析:\n")
        self.analyse_deviate(self.cpdf, "diff")
        self.analyse_percentile(self.cpdf, "diff")
        self.analyse_ud(self.cpdf, "real", "est")

    @staticmethod
    def analyse_ud(cpdf, col1, col2):
        """


        :param cpdf: pd.DataFrame, with col1 as real netvalue and col2 as prediction difference
        :param col1: str.
        :param col2: str.
        :return:
        """
        uu, ud, dd, du, count = 0, 0, 0, 0, 0
        # uu 实际上涨，real-est>0 (预测涨的少)
        # ud 预测涨的多
        # du 预测跌的多
        # dd 预测跌的少
        for i, row in cpdf.iterrows():
            if row[col1] >= 0 and row[col2] > 0:
                uu += 1
            elif row[col1] >= 0 >= row[col2]:
                ud += 1
            elif row[col1] < 0 < row[col2]:
                du += 1
            else:
                dd += 1
            count += 1
        print(
            "\n涨跌偏差分析:",
            "\n预测涨的比实际少: ",
            round(uu / count, 2),
            "\n预测涨的比实际多: ",
            round(ud / count, 2),
            "\n预测跌的比实际多: ",
            round(du / count, 2),
            "\n预测跌的比实际少: ",
            round(dd / count, 2),
        )

    @staticmethod
    def analyse_percentile(cpdf, col):
        percentile = [1, 5, 25, 50, 75, 95, 99]
        r = [round(d, 3) for d in np.percentile(list(cpdf[col]), percentile)]
        print(
            "\n预测偏差分位:",
            "\n1% 分位: ",
            r[0],
            "\n5% 分位: ",
            r[1],
            "\n25% 分位: ",
            r[2],
            "\n50% 分位: ",
            r[3],
            "\n75% 分位: ",
            r[4],
            "\n95% 分位: ",
            r[5],
            "\n99% 分位: ",
            r[6],
        )

    @staticmethod
    def analyse_deviate(cpdf, col):
        l = np.array(cpdf[col])
        d1, d2 = np.mean(np.abs(l)), np.sqrt(np.mean(l ** 2))
        print("\n平均偏离: ", d1, "\n标准差偏离： ", d2)
