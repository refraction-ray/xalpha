# -*- coding: utf-8 -*-
"""
module for mul and mulfix class: fund combination management
"""

import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Pie, ThemeRiver

from xalpha.cons import convert_date, myround, pie_opts, yesterdaydash, yesterdayobj
from xalpha.evaluate import evaluate
from xalpha.exceptions import FundTypeError, TradeBehaviorError
from xalpha.record import record, irecord
from xalpha.indicator import indicator
from xalpha.info import cashinfo, fundinfo, mfundinfo
from xalpha.trade import bottleneck, trade, turnoverrate, vtradevolume, xirrcal, itrade


class mul:
    """
    multiple fund positions manage class

    :param fundtradeobj: list of trade obj which you want to analyse together
    :param status: the status table of trade, all code in this table would be considered.
            one must provide one of the two paramters, if both are offered, status will be overlooked
            可以是场内记账单 DataFrame，也可以是 record 对象。
    :param istatus: 场内交易账单，也可以是 irecord 对象。
            若提供，则场内外交易联合统计展示。该选项只保证 ``combsummary`` 方法可正常使用，不保证 ``mul`` 类的其他方法可用。
    :param property: Dict[fundcode, property_number]. property number 的解释：
            int. 1: 基金申购采取分位以后全舍而非四舍五入（这种基金是真实存在的==）。2：基金默认分红再投入（0 则是默认现金分红）。4：基金赎回按净值处理（暂时只支持货币基金，事实上无法精确支持按份额赎回的净值型基金）。将想要的性质数值相加即可，类似 *nix 上的 xwr 系统。
    :param fetch: boolean, when open the fetch option, info class will try fetching from local files first in the init
    :param save: boolean, when open the save option, info classes automatically save the class to files
    :param path: string, the file path prefix of IO, or object or engine from sqlalchemy to connect sql database
    :param form: string, the format of IO, options including: 'csv','sql'
    """

    def __init__(
        self,
        *fundtradeobj,
        status=None,
        istatus=None,
        property=None,
        fetch=False,
        save=False,
        path="",
        form="csv"
    ):
        if isinstance(status, record):
            if not property:
                property = getattr(status, "property", {})
            status = status.status
        elif not property:
            property = {}
        self.is_in = False
        if fundtradeobj:
            for t in fundtradeobj:
                if isinstance(t, itrade):
                    self.is_in = True
                break
        else:
            # warning: not a very good way to automatic generate these fund obj
            # because there might be some funds use round_down for share calculation, ie, label=2 must be given
            # unless you are sure corresponding funds are added to the droplist
            fundtradeobj = []
            for code in status.columns[1:]:
                # r1, d2, v4 p = r+d+v
                p = property.get(code, 0)
                round_label = p % 2
                dividend_label = ((p - round_label) / 2) % 2
                value_label = ((p - round_label - dividend_label) / 4) % 2
                try:
                    fundtradeobj.append(
                        trade(
                            fundinfo(
                                code,
                                round_label=round_label,
                                dividend_label=dividend_label,
                                fetch=fetch,
                                save=save,
                                path=path,
                                form=form,
                            ),
                            status,
                        )
                    )
                except FundTypeError:
                    fundtradeobj.append(
                        trade(
                            mfundinfo(
                                code,
                                round_label=round_label,
                                value_label=value_label,
                                fetch=fetch,
                                save=save,
                                path=path,
                                form=form,
                            ),
                            status,
                        )
                    )
            if istatus:
                self.is_in = True
                if isinstance(istatus, irecord):
                    istatus = istatus.status
                for code in istatus.code.unique():
                    fundtradeobj.append(itrade(code, istatus))
        self.fundtradeobj = tuple(fundtradeobj)
        self.totcftable = self._mergecftb()

    def tot(self, prop="基金现值", date=yesterdayobj()):
        """
        sum of all the values from one prop of fund daily report,
        of coures many of the props make no sense to sum

        :param prop: string defined in the daily report dict,
            typical one is 'currentvalue' or 'originalpurchase'
        """
        res = 0
        for fund in self.fundtradeobj:
            res += fund.dailyreport().iloc[0][prop]
        return res

    def combsummary(self, date=yesterdayobj()):
        """
        brief report table of every funds and the combination investment

        :param date: string or obj of date, show info of the date given
        :returns: empty dict if nothing is remaining that date
            dict of various data on the trade positions
        """
        date = convert_date(date)
        columns = [
            "基金名称",
            "基金代码",
            "当日净值",
            "单位成本",
            "持有份额",
            "基金现值",
            "基金总申购",
            "历史最大占用",
            "基金持有成本",
            "基金分红与赎回",
            "换手率",
            "基金收益总额",
            "投资收益率",
        ]
        summarydf = pd.DataFrame([], columns=columns)
        for fund in self.fundtradeobj:
            summarydf = summarydf.append(
                fund.dailyreport(date), ignore_index=True, sort=True
            )
        tname = "总计"
        tcode = "total"
        tunitvalue = float("NaN")
        tunitcost = float("NaN")
        tholdshare = float("NaN")
        tcurrentvalue = summarydf["基金现值"].sum()
        tpurchase = summarydf["基金总申购"].sum()
        tbtnk = bottleneck(self.totcftable[self.totcftable["date"] <= date])
        tcost = summarydf["基金持有成本"].sum()
        toutput = summarydf["基金分红与赎回"].sum()
        tturnover = turnoverrate(self.totcftable[self.totcftable["date"] <= date], date)
        # 计算的是总系统作为整体和外界的换手率，而非系统各成分之间的换手率
        tearn = summarydf["基金收益总额"].sum()
        trate = round(tearn / tbtnk * 100, 4)
        trow = pd.DataFrame(
            [
                [
                    tname,
                    tcode,
                    tunitvalue,
                    tunitcost,
                    tholdshare,
                    tcurrentvalue,
                    tpurchase,
                    tbtnk,
                    tcost,
                    toutput,
                    tturnover,
                    tearn,
                    trate,
                ]
            ],
            columns=columns,
        )
        summarydf = summarydf.append(trow, ignore_index=True, sort=True)

        return summarydf[columns].sort_values(by="基金现值", ascending=False)

    def _mergecftb(self):
        """
        merge the different cftable for different funds into one table
        """
        dtlist = []
        for fund in self.fundtradeobj:
            dtlist2 = []
            for _, row in fund.cftable.iterrows():
                dtlist2.append((row["date"], row["cash"]))
            dtlist.extend(dtlist2)

        nndtlist = set([item[0] for item in dtlist])
        nndtlist = sorted(list(nndtlist), key=lambda x: x)
        reslist = []
        for date in nndtlist:
            reslist.append(sum([item[1] for item in dtlist if item[0] == date]))
        df = pd.DataFrame(data={"date": nndtlist, "cash": reslist})
        df = df[df["cash"] != 0]
        df = df.reset_index(drop=True)
        return df

    def xirrrate(self, date=yesterdayobj(), guess=0.1):
        """
        xirr rate evauation of the whole invest combination
        """
        return xirrcal(self.totcftable, self.fundtradeobj, date, guess)

    def evaluation(self, start=None):
        """
        give the evaluation object to analysis funds properties themselves instead of trades

        :returns: :class:`xalpha.evaluate.evaluate` object, with referenced funds the same as funds
            we invested
        """
        if self.is_in:
            raise NotImplementedError()
        case = evaluate(
            *[fundtrade.aim for fundtrade in self.fundtradeobj], start=start
        )
        return case

    def v_positions(self, date=yesterdayobj(), vopts=None):
        """
        pie chart visualization of positions ratio in combination
        """
        sdata = sorted(
            [
                (fob.name, fob.briefdailyreport(date).get("currentvalue", 0))
                for fob in self.fundtradeobj
            ],
            key=lambda x: x[1],
            reverse=True,
        )

        pie = Pie()
        if vopts is None:
            vopts = pie_opts
        pie.add(series_name="总值占比", data_pair=sdata)
        pie.set_global_opts(**vopts)
        return pie.render_notebook()

    def v_positions_history(self, end=yesterdaydash(), **vkwds):
        """
        river chart visulization of positions ratio history
        use text size to avoid legend overlap in some sense, eg. legend_text_size=8
        """
        start = self.totcftable.iloc[0].date
        times = pd.date_range(start, end)
        tdata = []
        for date in times:
            sdata = sorted(
                [
                    (date, fob.briefdailyreport(date).get("currentvalue", 0), fob.name,)
                    for fob in self.fundtradeobj
                ],
                key=lambda x: x[1],
                reverse=True,
            )
            tdata.extend(sdata)

        tr = ThemeRiver()
        tr.add(
            series_name=[foj.name for foj in self.fundtradeobj],
            data=tdata,
            label_opts=opts.LabelOpts(is_show=False),
            singleaxis_opts=opts.SingleAxisOpts(type_="time", pos_bottom="10%"),
        )

        return tr.render_notebook()

    def v_tradevolume(self, freq="D"):
        """
        visualization on trade summary of the funds combination

        :param freq: one character string, frequency label, now supporting D for date,
            W for week and M for month, namely the trade volume is shown based on the time unit
        :returns: ``pyecharts.Bar()``
        """
        return vtradevolume(self.totcftable, freq=freq)


class mulfix(mul, indicator):
    """
    introduce cash to make a closed investment system, where netvalue analysis can be applied
    namely the totcftable only has one row at the very beginning

    :param fundtradeobj: trade obj to be include
    :param status: status table,  if no trade obj is provided, it will include all fund
            based on code in status table
    :param property: Dict[fundcode, property_number]. property number 的解释：
            int. 1: 基金申购采取分位以后全舍而非四舍五入（这种基金是真实存在的==）。2：基金默认分红再投入（0 则是默认现金分红）。4：基金赎回按净值
    :param fetch: boolean, when open the fetch option, info class will try fetching from local files first in the init
    :param save: boolean, when open the save option, info classes automatically save the class to files
    :param path: string, the file path prefix of IO, or object or engine from sqlalchemy to connect sql database
    :param form: string, the format of IO, options including: 'csv','sql'
    :param totmoney: positive float, the total money as the input at the beginning
    :param cashobj: cashinfo object, which is designed to balance the cash in and out
    """

    def __init__(
        self,
        *fundtradeobj,
        status=None,
        property=None,
        fetch=False,
        save=False,
        path="",
        form="csv",
        totmoney=100000,
        cashobj=None
    ):
        super().__init__(
            *fundtradeobj,
            status=status,
            property=property,
            fetch=fetch,
            save=save,
            path=path,
            form=form
        )
        if cashobj is None:
            cashobj = cashinfo()
        self.totmoney = totmoney
        nst = mulfix._vcash(totmoney, self.totcftable, cashobj)
        cashtrade = trade(cashobj, nst)
        # 		 super().__init__(*self.fundtradeobj, cashtrade)
        self.fundtradeobj = list(self.fundtradeobj)
        self.fundtradeobj.append(cashtrade)
        self.fundtradeobj = tuple(self.fundtradeobj)
        btnk = bottleneck(self.totcftable)
        if btnk > totmoney:
            raise TradeBehaviorError("the initial total cash is too low")
        self.totcftable = pd.DataFrame(
            data={"date": [nst.iloc[0].date], "cash": [-totmoney]}
        )

    def _vcash(totmoney, totcftable, cashobj):
        """
        return a virtue status table with a mf(cash) column based on the given tot money and cftable
        """
        cashl = []
        cashl.append(totmoney + totcftable.iloc[0].cash)
        for i in range(len(totcftable) - 1):
            date = totcftable.iloc[i + 1].date
            delta = totcftable.iloc[i + 1].cash
            if delta < 0:
                cashl.append(
                    myround(
                        delta
                        / cashobj.price[cashobj.price["date"] <= date].iloc[-1].netvalue
                    )
                )
            else:
                cashl.append(delta)
        datadict = {"date": totcftable.loc[:, "date"], "mf": cashl}
        return pd.DataFrame(data=datadict)

    def unitvalue(self, date=yesterdayobj()):
        """
        :returns: float at unitvalue of the whole investment combination
        """
        date = convert_date(date)
        res = 0
        for fund in self.fundtradeobj:
            res += fund.briefdailyreport(date).get("currentvalue", 0)
        return res / self.totmoney


class imul(mul):
    def __init__(self, *fundtradeobj, status=None, istatus=None):
        """
        对场内投资组合进行分析的类

        :param fundtradeobj: itrade objects.
        :param status: 场内格式记账单，或 irecord 对象。
        """

        if not fundtradeobj:
            fundtradeobj = []
            if not status:
                status = istatus
            if isinstance(status, irecord):
                status = status.status
            for code in status.code.unique():
                fundtradeobj.append(itrade(code, status))
        self.fundtradeobj = tuple(fundtradeobj)
        self.totcftable = self._mergecftb()
        self.is_in = True


Mul = mul
MulFix = mulfix
IMul = imul
