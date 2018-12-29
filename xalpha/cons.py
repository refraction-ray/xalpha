# -*- coding: utf-8 -*-
'''
basic constants and functions
'''

import datetime as dt
from decimal import Decimal
from scipy import optimize
import pandas as pd

# date obj of today
today = lambda: dt.datetime.combine(dt.date.today(), dt.time.min)

# string for yesterday, only used for indexinfo url
yesterday = lambda: dt.datetime.strftime((dt.datetime.now() - dt.timedelta(1)), '%Y%m%d')

# string for yesterday with dash
yesterdaydash = lambda: dt.datetime.strftime((dt.datetime.now() - dt.timedelta(1)), '%Y-%m-%d')

# datetime obj for yesterdate date with time set to be 0:0:0
yesterdayobj = lambda: dt.datetime.strptime(yesterdaydash(), '%Y-%m-%d')

# list: all the trade date of domestic stock market in the form of string
caldate = pd.read_csv('http://file.tushare.org/tsdata/calAll.csv')
opendate = list(caldate[caldate['isOpen'] == 1]['calendarDate'])
# directly use the tushare API instead of import tushare package for simplicity
# opendate = list(ts.trade_cal()[ts.trade_cal()['isOpen']==1]['calendarDate']) 

# fund code list which always round down for the purchase share approximation
droplist = ['003318', '000311']


def xnpv(rate, cashflows):
    '''
    give the current cash value based on future cashflows

    :param rate: float, the preset year rate
    :param cashflows: a list, in which each element is a tuple of the form (date, amount),
        where date is a datetime object and amount is an integer or floating number.
        Cash outflows (investments) are represented with negative amounts,
        and cash inflows (returns) are positive amounts.
    :returns: a single float value which is the NPV of the given cash flows
    '''
    chron_order = sorted(cashflows, key=lambda x: x[0])
    t0 = chron_order[0][0]
    return sum([cf / (1 + rate) ** ((t - t0).days / 365.0) for (t, cf) in chron_order])


def xirr(cashflows, guess=0.1):
    '''
    calculate the Internal Rate of Return of a series of cashflows at irregular intervals.

    :param cashflows: a list, in which each element is a tuple of the form (date, amount),
        where date is a datetime object and amount is an integer or floating number.
        Cash outflows (investments) are represented with negative amounts,
        and cash inflows (returns) are positive amounts.
    :param guess: floating number, a guess at the xirr rate solution to be used
        as a starting point for the numerical solution
    :returns: the IRR as a single floating number
    '''
    return optimize.newton(lambda r: xnpv(r, cashflows), guess)


def myround(num, label=1):
    '''
    correct implementation of round with round half up, round to 2 decimals

    :param num: the floating number, to be rounded
    :param label: integer 1 or 2, 1 for round half up while 2 for always round down
    :returns: the float number after rounding, with two decimals
    '''
    if label == 1:
        res = float(Decimal(str(num)).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP'))
    elif label == 2:  # for jingshunchangcheng... who just omit the overflow share behind 2 decimal
        res = float(Decimal(str(num)).quantize(Decimal('0.01'), rounding='ROUND_DOWN'))
    return res


def convert_date(date):
    '''
    convert date into datetime object

    :param date: string of form '2017-01-01' or datetime object
    :returns: corresponding datetime object
    '''
    if isinstance(date, str):
        return pd.Timestamp(date)
    else:
        return date
