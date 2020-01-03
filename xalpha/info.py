# -*- coding: utf-8 -*-
"""
modules of info class, including cashinfo, indexinfo and fundinfo class
"""
import csv
import datetime as dt
import json
import re

import pandas as pd
import requests as rq
from bs4 import BeautifulSoup
from slimit import ast
from slimit.parser import Parser
from slimit.visitors import nodevisitor
from sqlalchemy import exc

import xalpha.remain as rm
from xalpha.cons import (
    convert_date,
    droplist,
    myround,
    opendate,
    yesterday,
    yesterdaydash,
    yesterdayobj,
)
from xalpha.exceptions import FundTypeError, TradeBehaviorError
from xalpha.indicator import indicator

_warnmess = "Something weird on redem fee, please adjust self.segment by hand"


def _download(url, tries=5):
    """
    wrapper of requests.get(), in case of internet failure

    :param url: string of the url
    :param tries: int, attempts to reconnect the url
    :return: request.get() object
    """
    for count in range(tries):
        try:
            page = rq.get(url)
            break
        except (ConnectionResetError, rq.exceptions.RequestException) as e:
            if count == tries - 1:
                raise e
    return page


def _shengoucal(sg, sgf, value, label):
    """
    Infer the share of buying fund by money input, the rate of fee in the unit of %,
        and netvalue of fund

    :param sg: positive float, 申购金额
    :param sgf: positive float, 申购费，以％为单位，如 0.15 表示 0.15%
    :param value: positive float, 对应产品的单位净值
    :param label: integer, 1 代表份额正常进行四舍五入， 2 代表份额直接舍去小数点两位之后。金额部分都是四舍五入
    :returns: tuple of two positive float, 净申购金额和申购份额
    """
    jsg = myround(sg / (1 + sgf * 1e-2))
    share = myround(jsg / value, label)
    return (jsg, share)


def _nfloat(string):
    """
    deal with comment column in fundinfo price table,
    positive value for fenhong and negative value for chaifen,
    keep other unrocognized pattern as original string

    :param string: string of input from original data
    :returns: make fenhong and songpei as float number
    """
    result = 0
    if string != '""' and string is not None:
        try:
            result = float(string)
        except ValueError:
            if re.match(r'"分红\D*(\d*\.\d*)\D*"', string):
                result = float(re.match(r'"分红\D*(\d*\.\d*)\D*"', string).group(1))
            elif re.match(r".*现金(\d*\.\d*)\D*", string):
                result = float(re.match(r".*现金(\d*\.\d*)\D*", string).group(1))
            elif re.match(r".*折算(\d*\.\d*)\D*", string):
                result = -float(re.match(r".*折算(\d*\.\d*)\D*", string).group(1))
            elif re.match(r'"拆分\D*(\d*\.\d*)\D*"', string):
                result = -float(re.match(r'"拆分\D*(\d*\.\d*)\D*"', string).group(1))
            else:
                print("The comment col cannot be converted: %s" % string)
                result = string
    return result


class basicinfo(indicator):
    """
    Base class for info of fund, index or even cash,
    which cannot be directly instantiate, the basic implementation consider
    redemption fee as zero when shuhui() function is implemented

    :param code: string of code for specific product
    :param fetch: boolean, when open the fetch option, the class will try fetching from local files first in the init
    :param save: boolean, when open the save option, automatically save the class to files
    :param path: string, the file path prefix of IO. Or in sql case, path is the engine from sqlalchemy.
    :param form: string, the format of IO, options including: 'csv','sql'
    :param label: int, 1 or 2, label to the different round scheme of shares, reserved for fundinfo class
    """

    def __init__(self, code, fetch=False, save=False, path="", form="csv", label=1):
        # 增量 IO 的逻辑都由 basicinfo 类来处理，对于具体的子类，只需实现_save_form 和 _fetch_form 以及 update 函数即可
        self.code = code
        self.format = form
        self.label = label
        self.specialdate = []
        self.fenhongdate = []
        self.zhesuandate = []
        if fetch is False:
            self._basic_init()  # update self. name rate and price table
        else:
            try:
                self.fetch(path, self.format)
                df = self.update()  # update the price table as well as the file
                if (df is not None) and save is True:
                    self.save(path, self.format, option="a", delta=df)

            except (FileNotFoundError, exc.ProgrammingError) as e:
                print("no saved copy of %s" % self.code)
                fetch = False
                self._basic_init()

        if (save is True) and (fetch is False):
            self.save(path, self.format)

    def _basic_init(self):
        """
        set self. name rate and price (dataframe) as well as other necessary attr of info()
        """
        # below lines are just showcase, this function must be rewrite by child classes
        # self.name = 'unknown'
        # self.rate = 0
        # self.price = pd.DataFrame(data={'date':[],'netvalue':[],'comment':[]})
        raise NotImplementedError

    def shengou(self, value, date):
        """
        give the realdate deltacash deltashare tuple based on purchase date and purchase amount
        if the date is not a trade date, then the purchase would happen on the next trade day, if the date is
        in the furture, then the trade date is taken as yesterday.

        :param value: the money for purchase
        :param date: string or object of date
        :returns: three elements tuple, the first is the actual dateobj of commit
            the second is a negative float for cashin,
            the third is a positive float for share increase
        """
        row = self.price[self.price["date"] >= date].iloc[0]
        share = _shengoucal(value, self.rate, row.netvalue, label=self.label)[1]
        return (row.date, -myround(value), share)

    def shuhui(self, share, date, rem):
        """
        give the cashout considering redemption rates as zero.
        if the date is not a trade date, then the purchase would happen on the next trade day, if the date is
        in the furture, then the trade date is taken as yesterday.

        :param share: float or int, number of shares to be sold
        :param date: string or object of date
        :returns: three elements tuple, the first is dateobj
            the second is a positive float for cashout,
            the third is a negative float for share decrease
        """
        date = convert_date(date)
        tots = sum([remitem[1] for remitem in rem if remitem[0] <= date])
        if share > tots:
            sh = tots
        else:
            sh = share
        partprice = self.price[self.price["date"] >= date]
        if len(partprice) == 0:
            row = self.price[self.price["date"] < date].iloc[-1]
        else:
            row = partprice.iloc[0]
        value = myround(sh * row.netvalue)
        return (row.date, value, -myround(sh))

    def info(self):
        """
        print basic info on the class
        """
        print("fund name: %s" % self.name)
        print("fund code: %s" % self.code)
        print("fund purchase fee: %s%%" % self.rate)

    def __repr__(self):
        return self.name

    def save(self, path, form=None, option="r", delta=None):
        """
        save info to files, this function is designed to redirect to more specific functions

        :param path: string of the folder path prefix! or engine obj from sqlalchemy
        :param form: string, option:'csv'
        :param option: string, r for replace and a for append output
        :param delta: if option is a, you have to specify the delta which is the incremental part of price table
        """
        if form is None:
            form = self.format
        if form == "csv" and option == "r":
            self._save_csv(path)
        elif form == "csv" and option == "a":
            self._save_csv_a(path, delta)
        elif form == "sql" and option == "r":
            self._save_sql(path)
        elif form == "sql" and option == "a":
            self._save_sql_a(path, delta)

    def _save_csv_a(self, path, df):
        df.sort_index(axis=1).to_csv(
            path + self.code + ".csv",
            mode="a",
            header=None,
            index=False,
            date_format="%Y-%m-%d",
        )

    def _save_sql_a(self, path, df):
        df.sort_index(axis=1).to_sql(
            "xa" + self.code, path, if_exists="append", index=False
        )

    def fetch(self, path, form=None):
        """
        fetch info from files

        :param path: string of the folder path prefix! end with / in csv case;
            engine from sqlalchemy.create_engine() in sql case.
        :param form: string, option:'csv' or 'sql
        """
        if form is None:
            form = self.format
        if form == "csv":
            self._fetch_csv(path)
        elif form == "sql":
            self._fetch_sql(path)

    def update(self):
        """
        对类的价格表进行增量更新，并进行增量存储，适合 fetch 打开的情形

        :returns: the incremental part of price table or None if no incremental part exsits
        """
        raise NotImplementedError


class fundinfo(basicinfo):
    """
    class for specific fund with basic info and every day values
    所获得的基金净值数据一般截止到昨日。但注意QDII基金的净值数据会截止的更早，因此部分时间默认昨日的函数可能出现问题，
    处理QDII基金时，需要额外注意。

    :param code: str, 基金六位代码字符
    :param label: integer 1 or 2, 取2表示基金申购时份额直接舍掉小数点两位之后。当基金处于 cons.droplist 名单中时，
        label 总会被自动设置为2。非名单内基金可以显式令 label=2.
    :param fetch: boolean, when open the fetch option, the class will try fetching from local files first in the init
    :param save: boolean, when open the save option, automatically save the class to files
    :param path: string, the file path prefix of IO
    :param form: string, the format of IO, options including: 'csv'
    """

    def __init__(self, code, label=1, fetch=False, save=False, path="", form="csv"):
        if label == 2 or (code in droplist):
            self.label = 2  # the scheme of round down on share purchase
        else:
            self.label = 1

        self._url = (
            "http://fund.eastmoney.com/pingzhongdata/" + code + ".js"
        )  # js url api for info of certain fund
        self._feeurl = (
            "http://fund.eastmoney.com/f10/jjfl_" + code + ".html"
        )  # html url for trade fees info of certain fund

        super().__init__(
            code, fetch=fetch, save=save, path=path, form=form, label=self.label
        )

        self.special = self.price[self.price["comment"] != 0]
        self.specialdate = list(self.special["date"])
        # date with nonvanishing comment, usually fenhong or zhesuan
        try:
            self.fenhongdate = list(self.price[self.price["comment"] > 0]["date"])
            self.zhesuandate = list(self.price[self.price["comment"] < 0]["date"])
        except TypeError:
            print("There are still string comments for the fund!")

    def _basic_init(self):
        self._page = _download(self._url)
        if self._page.text[:800].find("Data_millionCopiesIncome") >= 0:
            raise FundTypeError("This code seems to be a mfund, use mfundinfo instead")

        parser = Parser()  # parse the js text of API page using slimit module
        tree = parser.parse(self._page.text)
        nodenet = [
            node.children()[0].children()[1]
            for node in nodevisitor.visit(tree)
            if isinstance(node, ast.VarStatement)
            and node.children()[0].children()[0].value == "Data_netWorthTrend"
        ][0]
        nodetot = [
            node.children()[0].children()[1]
            for node in nodevisitor.visit(tree)
            if isinstance(node, ast.VarStatement)
            and node.children()[0].children()[0].value == "Data_ACWorthTrend"
        ][0]
        ## timestamp transform tzinfo must be taken into consideration
        tz_bj = dt.timezone(dt.timedelta(hours=8))

        infodict = {
            "date": [
                dt.datetime.fromtimestamp(
                    int(nodenet.children()[i].children()[0].right.value) / 1e3, tz=tz_bj
                ).replace(tzinfo=None)
                for i in range(len(nodenet.children()))
            ],
            "netvalue": [
                float(nodenet.children()[i].children()[1].right.value)
                for i in range(len(nodenet.children()))
            ],
            "comment": [
                _nfloat(nodenet.children()[i].children()[3].right.value)
                for i in range(len(nodenet.children()))
            ],
        }

        if len(nodenet.children()) == len(
            nodetot.children()
        ):  # 防止总值和净值数据量不匹配，已知有该问题的基金：502010
            infodict["totvalue"] = [
                float(nodetot.children()[i].children()[1].value)
                for i in range(len(nodenet.children()))
            ]

        rate = [
            node.children()[0].children()[1]
            for node in nodevisitor.visit(tree)
            if isinstance(node, ast.VarStatement)
            and (node.children()[0].children()[0].value == "fund_Rate")
        ][0]

        name = [
            node.children()[0].children()[1]
            for node in nodevisitor.visit(tree)
            if isinstance(node, ast.VarStatement)
            and (node.children()[0].children()[0].value == "fS_name")
        ][0]

        self.rate = float(
            rate.value.strip('"')
        )  # shengou rate in tiantianjijin, daeshengou rate discount is not considered
        self.name = name.value.strip('"')  # the name of the fund
        df = pd.DataFrame(data=infodict)
        df = df[df["date"].isin(opendate)]
        df = df.reset_index(drop=True)
        self.price = df[df["date"] <= yesterdaydash()]
        # deal with the redemption fee attrs finally
        self._feepreprocess()

    def _feepreprocess(self):
        """
        Preprocess to add self.feeinfo and self.segment attr according to redemption fee info
        """
        feepage = _download(self._feeurl)
        soup = BeautifulSoup(
            feepage.text, "lxml"
        )  # parse the redemption fee html page with beautiful soup
        self.feeinfo = [
            item.string
            for item in soup.findAll("a", {"name": "shfl"})[
                0
            ].parent.parent.next_sibling.next_sibling.find_all("td")
            if item.string != "---"
        ]
        self.segment = fundinfo._piecewise(self.feeinfo)

    @staticmethod
    def _piecewise(a):
        """
        Transform the words list into a pure number segment list for redemption fee, eg. [[0,7],[7,365],[365]]
        """
        b = [
            (
                a[2 * i]
                .replace("小于", "")
                .replace("大于", "")
                .replace("等于", "")
                .replace("个", "")
            ).split("，")
            for i in range(int(len(a) / 2))
        ]
        for j, tem in enumerate(b):
            for i, num in enumerate(tem):
                if num[-1] == "天":
                    num = int(num[:-1])
                elif num[-1] == "月":
                    num = int(num[:-1]) * 30
                else:
                    num = int(num[:-1]) * 365
                b[j][i] = num
        if len(b[0]) == 1:  # 有时赎回费会写大于等于一天
            b[0].insert(0, 0)
        elif len(b[0]) == 2:
            b[0][0] = 0
        else:
            print(_warnmess)
        for i in range(len(b) - 1):  # 有时赎回费两区间都是闭区间
            if b[i][1] - b[i + 1][0] == -1:
                b[i][1] = b[i + 1][0]
            elif b[i][1] == b[i + 1][0]:
                pass
            else:
                print(_warnmess)

        return b

    def feedecision(self, day):
        """
        give the redemption rate in percent unit based on the days difference between purchase and redemption

        :param day: integer， 赎回与申购时间之差的自然日数
        :returns: float，赎回费率，以％为单位
        """
        i = -1
        for seg in self.segment:
            i += 2
            if day - seg[0] >= 0 and (len(seg) == 1 or day - seg[-1] < 0):
                return float(self.feeinfo[i].strip("%"))
        return 0  # error backup, in case there is sth wrong in segment

    def shuhui(self, share, date, rem):
        """
        give the cashout based on rem term considering redemption rates

        :returns: three elements tuple, the first is dateobj
            the second is a positive float for cashout,
            the third is a negative float for share decrease
        """
        # 		 value = myround(share*self.price[self.price['date']==date].iloc[0].netvalue)
        date = convert_date(date)
        partprice = self.price[self.price["date"] >= date]
        if len(partprice) == 0:
            row = self.price[self.price["date"] < date].iloc[-1]
        else:
            row = partprice.iloc[0]
        soldrem, _ = rm.sell(rem, share, row.date)
        value = 0
        sh = myround(sum([item[1] for item in soldrem]))
        for d, s in soldrem:
            value += myround(
                s * row.netvalue * (1 - self.feedecision((row.date - d).days) * 1e-2)
            )
        return (row.date, value, -sh)

    def info(self):
        super().info()
        print("fund redemption fee info: %s" % self.feeinfo)

    def _save_csv(self, path):
        """
        save the information and pricetable into path+code.csv, not recommend to use manually,
        just set the save label to be true when init the object

        :param path:  string of folder path
        """
        s = json.dumps(
            {
                "feeinfo": self.feeinfo,
                "name": self.name,
                "rate": self.rate,
                "segment": self.segment,
            }
        )
        df = pd.DataFrame(
            [[s, 0, 0, 0]], columns=["date", "netvalue", "comment", "totvalue"]
        )
        df = df.append(self.price, ignore_index=True, sort=True)
        df.sort_index(axis=1).to_csv(
            path + self.code + ".csv", index=False, date_format="%Y-%m-%d"
        )

    def _fetch_csv(self, path):
        """
        fetch the information and pricetable from path+code.csv, not recommend to use manually,
        just set the fetch label to be true when init the object

        :param path:  string of folder path
        """
        try:
            content = pd.read_csv(path + self.code + ".csv")
            pricetable = content.iloc[1:]
            datel = list(pd.to_datetime(pricetable.date))
            self.price = pricetable[["netvalue", "totvalue", "comment"]]
            self.price["date"] = datel
            saveinfo = json.loads(content.iloc[0].date)
            if not isinstance(saveinfo, dict):
                raise FundTypeError("This csv doesn't looks like from fundinfo")
            self.segment = saveinfo["segment"]
            self.feeinfo = saveinfo["feeinfo"]
            self.name = saveinfo["name"]
            self.rate = saveinfo["rate"]
        except FileNotFoundError as e:
            # print('no saved copy of fund %s' % self.code)
            raise e

    def _save_sql(self, path):
        """
        save the information and pricetable into sql, not recommend to use manually,
        just set the save label to be true when init the object

        :param path:  engine object from sqlalchemy
        """
        s = json.dumps(
            {
                "feeinfo": self.feeinfo,
                "name": self.name,
                "rate": self.rate,
                "segment": self.segment,
            }
        )
        df = pd.DataFrame(
            [[pd.Timestamp("1990-01-01"), 0, s, 0]],
            columns=["date", "netvalue", "comment", "totvalue"],
        )
        df = df.append(self.price, ignore_index=True, sort=True)
        df.sort_index(axis=1).to_sql(
            "xa" + self.code, con=path, if_exists="replace", index=False
        )

    def _fetch_sql(self, path):
        """
        fetch the information and pricetable from sql, not recommend to use manually,
        just set the fetch label to be true when init the object

        :param path:  engine object from sqlalchemy
        """
        try:
            content = pd.read_sql("xa" + self.code, path)
            pricetable = content.iloc[1:]
            commentl = [float(com) for com in pricetable.comment]
            self.price = pricetable[["date", "netvalue", "totvalue"]]
            self.price["comment"] = commentl
            saveinfo = json.loads(content.iloc[0].comment)
            if not isinstance(saveinfo, dict):
                raise FundTypeError("This csv doesn't looks like from fundinfo")
            self.segment = saveinfo["segment"]
            self.feeinfo = saveinfo["feeinfo"]
            self.name = saveinfo["name"]
            self.rate = saveinfo["rate"]
        except exc.ProgrammingError as e:
            # print('no saved copy of %s' % self.code)
            raise e

    def update(self):
        """
        function to incrementally update the pricetable after fetch the old one
        """
        lastdate = self.price.iloc[-1].date
        diffdays = (yesterdayobj() - lastdate).days
        if (
            diffdays == 0
        ):  ## for some QDII, this value is 1, anyways, trying update is compatible (d+2 update)
            return None
        elif diffdays <= 10:
            self._updateurl = (
                "http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code="
                + self.code
                + "&page=1&per="
                + str(diffdays)
            )
            con = _download(self._updateurl)
            soup = BeautifulSoup(con.text, "lxml")
            items = soup.findAll("td")
        elif (
            diffdays > 10
        ):  ## there is a 20 item per page limit in the API, so to be safe, we query each page by 10 items only
            items = []
            for pg in range(1, int(diffdays / 10) + 2):
                self._updateurl = (
                    "http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code="
                    + self.code
                    + "&page="
                    + str(pg)
                    + "&per=10"
                )
                con = _download(self._updateurl)
                soup = BeautifulSoup(con.text, "lxml")
                items.extend(soup.findAll("td"))
        else:
            raise TradeBehaviorError(
                "Weird incremental update: the saved copy has future records"
            )

        date = []
        netvalue = []
        totvalue = []
        comment = []
        for i in range(int(len(items) / 7)):
            ts = pd.Timestamp(items[7 * i].string)
            if (ts - lastdate).days > 0:
                date.append(ts)
                netvalue.append(float(items[7 * i + 1].string))
                totvalue.append(float(items[7 * i + 2].string))
                comment.append(_nfloat(items[7 * i + 6].string))
            else:
                break
        df = pd.DataFrame(
            {
                "date": date,
                "netvalue": netvalue,
                "totvalue": totvalue,
                "comment": comment,
            }
        )
        df = df.iloc[::-1]  ## reverse the time order
        df = df[df["date"].isin(opendate)]
        df = df.reset_index(drop=True)
        df = df[df["date"] <= yesterdayobj()]
        if len(df) != 0:
            self.price = self.price.append(df, ignore_index=True, sort=True)
            return df


class indexinfo(basicinfo):
    """
    Get everyday close price of specific index.
    In self.price table, totvalue column is the real index
    while netvalue comlumn is normalized to 1 for the start date.
    In principle, this class can also be used to save stock prices but the price is without adjusted.

    :param code: string with seven digitals! note the code here has an extra digit at the beginning,
        0 for sh and 1 for sz.
    :param fetch: boolean, when open the fetch option, the class will try fetching from local files first in the init
    :param save: boolean, when open the save option, automatically save the class to files
    :param path: string, the file path prefix of IO
    :param form: string, the format of IO, options including: 'csv'
    """

    def __init__(self, code, fetch=False, save=False, path="", form="csv"):
        date = yesterday()
        self.rate = 0
        self._url = (
            "http://quotes.money.163.com/service/chddata.html?code="
            + code
            + "&start=19901219&end="
            + date
            + "&fields=TCLOSE"
        )
        super().__init__(code, fetch=fetch, save=save, path=path, form=form)

    def _basic_init(self):
        raw = _download(self._url)
        cr = csv.reader(raw.text.splitlines(), delimiter=",")
        my_list = list(cr)
        factor = float(my_list[-1][3])
        dd = {
            "date": [
                dt.datetime.strptime(my_list[i + 1][0], "%Y-%m-%d")
                for i in range(len(my_list) - 1)
            ],
            "netvalue": [
                float(my_list[i + 1][3]) / factor for i in range(len(my_list) - 1)
            ],
            "totvalue": [float(my_list[i + 1][3]) for i in range(len(my_list) - 1)],
            "comment": [0 for _ in range(len(my_list) - 1)],
        }
        index = pd.DataFrame(data=dd)
        index = index.iloc[::-1]
        index = index.reset_index(drop=True)
        self.price = index[index["date"].isin(opendate)]
        self.price = self.price[self.price["date"] <= yesterdaydash()]
        self.name = my_list[-1][2]

    def _save_csv(self, path):
        """
        save the information and pricetable into path+code.csv, not recommend to use manually,
        just set the save label to be true when init the object

        :param path:  string of folder path
        """
        self.price.sort_index(axis=1).to_csv(
            path + self.code + ".csv", index=False, date_format="%Y-%m-%d"
        )

    def _fetch_csv(self, path):
        """
        fetch the information and pricetable from path+code.csv, not recommend to use manually,
        just set the fetch label to be true when init the object

        :param path:  string of folder path
        """
        try:
            pricetable = pd.read_csv(path + self.code + ".csv")
            datel = list(pd.to_datetime(pricetable.date))
            self.price = pricetable[["netvalue", "totvalue", "comment"]]
            self.price["date"] = datel

        except FileNotFoundError as e:
            # print('no saved copy of %s' % self.code)
            raise e

    def _save_sql(self, path):
        """
        save the information and pricetable into sql, not recommend to use manually,
        just set the save label to be true when init the object

        :param path:  engine object from sqlalchemy
        """
        self.price.sort_index(axis=1).to_sql(
            "xa" + self.code, con=path, if_exists="replace", index=False
        )

    def _fetch_sql(self, path):
        """
        fetch the information and pricetable from sql, not recommend to use manually,
        just set the fetch label to be true when init the object

        :param path:  engine object from sqlalchemy
        """
        try:
            pricetable = pd.read_sql("xa" + self.code, path)
            self.price = pricetable

        except exc.ProgrammingError as e:
            # print('no saved copy of %s' % self.code)
            raise e

    def update(self):
        lastdate = self.price.iloc[-1].date
        lastdatestr = lastdate.strftime("%Y%m%d")
        weight = self.price.iloc[1].totvalue
        self._updateurl = (
            "http://quotes.money.163.com/service/chddata.html?code="
            + self.code
            + "&start="
            + lastdatestr
            + "&end="
            + yesterday()
            + "&fields=TCLOSE"
        )
        df = pd.read_csv(self._updateurl, encoding="gb2312")
        self.name = df.iloc[0].loc["名称"]
        if len(df) > 1:
            df = df.rename(columns={"收盘价": "totvalue"})
            df["date"] = pd.to_datetime(df.日期)
            df = df.drop(["股票代码", "名称", "日期"], axis=1)
            df["netvalue"] = df.totvalue / weight
            df["comment"] = [0 for _ in range(len(df))]
            df = df.iloc[::-1].iloc[1:]
            df = df[df["date"].isin(opendate)]
            df = df.reset_index(drop=True)
            df = df[df["date"] <= yesterdayobj()]
            self.price = self.price.append(df, ignore_index=True, sort=True)
            return df


class cashinfo(basicinfo):
    """
    A virtual class for remaining cash manage: behave like monetary fund

    :param interest: float, daily rate in the unit of 100%, note this is not a year return rate!
    :param start: str of date or dateobj, the virtual starting date of the cash fund
    """

    def __init__(self, interest=0.0001, start="2012-01-01"):
        self.interest = interest
        start = convert_date(start)
        self.start = start
        super().__init__("mf")

    def _basic_init(self):
        self.name = "货币基金"
        self.rate = 0
        datel = list(
            pd.date_range(dt.datetime.strftime(self.start, "%Y-%m-%d"), yesterdaydash())
        )
        valuel = []
        for i, date in enumerate(datel):
            valuel.append((1 + self.interest) ** i)
        dfdict = {
            "date": datel,
            "netvalue": valuel,
            "totvalue": valuel,
            "comment": [0 for _ in datel],
        }
        df = pd.DataFrame(data=dfdict)
        self.price = df[df["date"].isin(opendate)]


class mfundinfo(basicinfo):
    """
    真实的货币基金类，可以通过货币基金六位代码，来获取真实的货币基金业绩，并进行交易回测等

    :param code: string of six digitals, code of real monetnary fund
    :param fetch: boolean, when open the fetch option, the class will try fetching from local files first in the init
    :param save: boolean, when open the save option, automatically save the class to files
    :param path: string, the file path prefix of IO
    :param form: string, the format of IO, options including: 'csv'

    """

    def __init__(self, code, fetch=False, save=False, path="", form="csv"):
        self._url = "http://fund.eastmoney.com/pingzhongdata/" + code + ".js"
        self.rate = 0
        super().__init__(code, fetch=fetch, save=save, path=path, form=form)

    def _basic_init(self):
        self._page = _download(self._url)
        if self._page.text[:800].find("Data_fundSharesPositions") >= 0:
            raise FundTypeError("This code seems to be a fund, use fundinfo instead")

        parser = Parser()
        tree = parser.parse(self._page.text)
        nodenet = [
            node.children()[0].children()[1]
            for node in nodevisitor.visit(tree)
            if isinstance(node, ast.VarStatement)
            and node.children()[0].children()[0].value == "Data_millionCopiesIncome"
        ][0]
        name = [
            node.children()[0].children()[1]
            for node in nodevisitor.visit(tree)
            if isinstance(node, ast.VarStatement)
            and (node.children()[0].children()[0].value == "fS_name")
        ][0]
        self.name = name.value.strip('"')
        tz_bj = dt.timezone(dt.timedelta(hours=8))
        datel = [
            dt.datetime.fromtimestamp(
                int(nodenet.children()[i].children()[0].value) / 1e3, tz=tz_bj
            ).replace(tzinfo=None)
            for i in range(len(nodenet.children()))
        ]
        ratel = [
            float(nodenet.children()[i].children()[1].value)
            for i in range(len(nodenet.children()))
        ]
        netvalue = [1]
        for dailyrate in ratel:
            netvalue.append(netvalue[-1] * (1 + dailyrate * 1e-4))
        netvalue.remove(1)

        df = pd.DataFrame(
            data={
                "date": datel,
                "netvalue": netvalue,
                "totvalue": netvalue,
                "comment": [0 for _ in datel],
            }
        )
        df = df[df["date"].isin(opendate)]
        df = df.reset_index(drop=True)
        self.price = df[df["date"] <= yesterdaydash()]

    def _save_csv(self, path):
        """
        save the information and pricetable into path+code.csv, not recommend to use manually,
        just set the save label to be true when init the object

        :param path:  string of folder path
        """
        df = pd.DataFrame(
            [[0, 0, self.name, 0]], columns=["date", "netvalue", "comment", "totvalue"]
        )
        df = df.append(self.price, ignore_index=True, sort=True)
        df.sort_index(axis=1).to_csv(
            path + self.code + ".csv", index=False, date_format="%Y-%m-%d"
        )

    def _fetch_csv(self, path):
        """
        fetch the information and pricetable from path+code.csv, not recommend to use manually,
        just set the fetch label to be true when init the object

        :param path:  string of folder path
        """
        try:
            content = pd.read_csv(path + self.code + ".csv")
            pricetable = content.iloc[1:]
            datel = list(pd.to_datetime(pricetable.date))
            self.price = pricetable[["netvalue", "totvalue", "comment"]]
            self.price["date"] = datel
            self.name = content.iloc[0].comment
        except FileNotFoundError as e:
            # print('no saved copy of %s' % self.code)
            raise e

    def _save_sql(self, path):
        """
        save the information and pricetable into sql, not recommend to use manually,
        just set the save label to be true when init the object

        :param path:  engine object from sqlalchemy
        """
        s = json.dumps({"name": self.name})
        df = pd.DataFrame(
            [[pd.Timestamp("1990-01-01"), 0, s, 0]],
            columns=["date", "netvalue", "comment", "totvalue"],
        )
        df = df.append(self.price, ignore_index=True, sort=True)
        df.sort_index(axis=1).to_sql(
            "xa" + self.code, con=path, if_exists="replace", index=False
        )

    def _fetch_sql(self, path):
        """
        fetch the information and pricetable from sql, not recommend to use manually,
        just set the fetch label to be true when init the object

        :param path:  engine object from sqlalchemy
        """
        try:
            content = pd.read_sql("xa" + self.code, path)
            pricetable = content.iloc[1:]
            commentl = [float(com) for com in pricetable.comment]
            self.price = pricetable[["date", "netvalue", "totvalue"]]
            self.price["comment"] = commentl
            self.name = json.loads(content.iloc[0].comment)["name"]
        except exc.ProgrammingError as e:
            # print('no saved copy of %s' % self.code)
            raise e

    def update(self):
        """
        function to incrementally update the pricetable after fetch the old one
        """
        lastdate = self.price.iloc[-1].date
        startvalue = self.price.iloc[-1].totvalue
        diffdays = (yesterdayobj() - lastdate).days
        if diffdays == 0:
            return None
        elif diffdays <= 10:
            self._updateurl = (
                "http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code="
                + self.code
                + "&page=1&per="
                + str(diffdays)
            )
            con = _download(self._updateurl)
            soup = BeautifulSoup(con.text, "lxml")
            items = soup.findAll("td")
        elif (
            diffdays > 10
        ):  ## there is a 20 item per page limit in the API, so to be safe, we query each page by 10 items only
            items = []
            for pg in range(1, int(diffdays / 10) + 2):
                self._updateurl = (
                    "http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code="
                    + self.code
                    + "&page="
                    + str(pg)
                    + "&per=10"
                )
                con = _download(self._updateurl)
                soup = BeautifulSoup(con.text, "lxml")
                items.extend(soup.findAll("td"))
        else:
            raise TradeBehaviorError(
                "Weird incremental update: the saved copy has future records"
            )

        date = []
        earnrate = []
        comment = []
        for i in range(int(len(items) / 6)):
            ts = pd.Timestamp(items[6 * i].string)
            if (ts - lastdate).days > 0:
                date.append(ts)
                earnrate.append(float(items[6 * i + 1].string) * 1e-4)
                comment.append(_nfloat(items[6 * i + 5].string))
        date = date[::-1]
        earnrate = earnrate[::-1]
        comment = comment[::-1]
        netvalue = [startvalue]
        for earn in earnrate:
            netvalue.append(netvalue[-1] * (1 + earn))
        netvalue.remove(startvalue)

        df = pd.DataFrame(
            {
                "date": date,
                "netvalue": netvalue,
                "totvalue": netvalue,
                "comment": comment,
            }
        )
        df = df[df["date"].isin(opendate)]
        df = df.reset_index(drop=True)
        df = df[df["date"] <= yesterdayobj()]
        if len(df) != 0:
            self.price = self.price.append(df, ignore_index=True, sort=True)
            return df
