# -*- coding: utf-8 -*-
'''
modules for policy making: generate status table for backtesting
'''
import pandas as pd
from xalpha.cons import yesterdaydash

class policy():
    '''
    base class for policy making, self.status to get the generating status table

    :param infoobj: info object as evidence for policy making
    :param start: string or object of date, the starting date for policy running
    :param end: string or object of date, the ending date for policy running
    :param totmoney: float or int, characteristic money value, 
        not necessary to be the total amount of money
    '''
    def __init__(self, infoobj, start, end=yesterdaydash, totmoney=100000):
        self.aim = infoobj
        self.totmoney = totmoney
        self.price = infoobj.price[(infoobj.price['date']>=start)&(infoobj.price['date']<=end)]
        self.start = self.price.iloc[0].date
        self.end = self.price.iloc[-1].date
        datel = []
        actionl = []
        for i, row in self.price.iterrows():
            date = row['date']
            action = self.status_gen(date)
            if action>0:
                datel.append(date)
                actionl.append(action)
            elif action<0:
                datel.append(date)
                actionl.append(action*0.005)
        df = pd.DataFrame(data={'date':datel,self.aim.code:actionl})
        self.status = df
        
    def status_gen(self, date):
        '''
        give policy decision based on given date

        :param date: date object
        :returns: float, positive for buying money, negative for selling shares
        '''
        raise NotImplementedError

class buyandhold(policy):
    '''
    simple policy class where buy at the start day and hold forever,
    始终选择分红再投入
    '''
    def status_gen(self, date):
        if date == self.start:
            return self.totmoney
        elif date in self.aim.specialdate:
            if self.price[self.price['date']==date].iloc[0].comment>0:
                return 0.05
            else:
                return 0
        else:
            return 0


class scheduled(policy):
    '''
    fixed schduled purchase for given date list

    :param infoobj: info obj
    :param totmoney: float, money value for purchase every time
    :param times: datelist for purchase date, eg ['2017-01-01','2017-07-07',...]
    '''
    def __init__(self, infoobj, totmoney, times):
        start = times[0]
        end = times[-1]
        self.times = times
        super().__init__(infoobj, start, end, totmoney)
        
    def status_gen(self, date):
        if date in self.times:
            return self.totmoney
        else:
            return 0
                