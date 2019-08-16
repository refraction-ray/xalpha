# -*- coding: utf-8 -*-
"""
module for status table IO
"""
import pandas as pd

from xalpha.cons import convert_date, yesterdayobj


class record:
    """
    basic class for status table read in from csv file.
    staus table 是关于对应基金的申赎寄账单，不同的行代表不同日期，不同的列代表不同基金，
    第一行各单元格分别为 date, 及基金代码。第一列各单元格分别为 date 及各个交易日期，形式 eg. 20170129
    表格内容中无交易可以直接为空或0，申购为正数，对应申购金额（申购费扣费前状态），赎回为负数，对应赎回份额，
    注意两者不同，恰好对应基金的金额申购份额赎回原则，记录精度均只完美支持一位小数。
    几个更具体的特殊标记：

    1. 小数点后第二位如果是5，且当日恰好为对应基金分红日，标志着选择了分红再投入的方式，否则默认分红拿现金

    2. 对于赎回的负数，如果是一个绝对值小于 0.005 的数，标记了赎回的份额占当时总份额的比例而非赎回的份额数目，
    其中0.005对应全部赎回，线性类推。eg. 0.001对应赎回20%。

    :param path: string for the csv file path
    :param readkwds: keywords options for pandas.read_csv() function. eg. skiprows=1, skipfooter=2,
        see more on `pandas doc <https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html>`_.
    """

    def __init__(self, path="input.csv", format="matrix", **readkwds):
        df = pd.read_csv(path, **readkwds)
        if format == "matrix":
            df.date = [
                # pd.Timestamp.strptime(str(int(df.iloc[i].date)), "%Y%m%d")
                # higher version of pandas timestamp doesn't support strptime anymore? why? what is the gain here?
                pd.to_datetime(str(int(df.iloc[i].date)), format="%Y%m%d")
                for i in range(len(df))
            ]
            df.fillna(0, inplace=True)
            self.status = df
        elif format == "list":
            fund = df.fund.unique()
            fund_s = ["{:06d}".format(i) for i in fund]
            date_s = df.date.unique()
            dfnew = pd.DataFrame(
                columns=["date"] + fund_s, index=date_s, dtype="float64"
            )
            dfnew.fillna(0, inplace=True)
            # dfnew["date"] = [pd.Timestamp.strptime(i, "%Y/%m/%d") for i in date_s]
            dfnew["date"] = [pd.to_datetime(i, format="%Y/%m/%d") for i in date_s]
            for i in range(len(df)):
                dfnew.at[df.iloc[i].date, "{:06d}".format(df.iloc[i].fund)] += df.iloc[
                    i
                ].trade
            dfnew = dfnew.sort_values(by=["date"])
            self.status = dfnew

    def sellout(self, date=yesterdayobj(), ratio=1):
        """
        Sell all the funds in the same ratio on certain day, it is a virtual process,
        so it can happen before the last action exsiting in the cftable, by sell out earlier,
        it means all actions behind vanish. The status table in self.status would be directly changed.

        :param date: string or datetime obj of the selling date
        :param ratio: float between 0 to 1, the ratio of selling for each funds
        """
        date = convert_date(date)
        s = self.status[self.status["date"] <= date]
        row = []
        ratio = ratio * 0.005
        for term in s.columns:
            if term != "date":
                row.append(-ratio)
            else:
                row.append(date)
        s = s.append(pd.DataFrame([row], columns=s.columns), ignore_index=True)
        self.status = s

    def save_csv(self, path=None, index=False, **tocsvkwds):
        """
        save the status table to csv file in path, no returns

        :param path: string of file path
        :param index: boolean, whether save the index to the csv file, default False
        :param tocsvkwds: keywords options for pandas.to_csv() function, see
            `pandas doc <https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.to_csv.html>`_.
        """
        self.status.to_csv(path, index=index, **tocsvkwds)
