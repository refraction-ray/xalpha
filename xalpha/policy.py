# -*- coding: utf-8 -*-
'''
modules for policy making: generate status table for backtesting
'''
import pandas as pd
from xalpha.cons import yesterdaydash, opendate, myround
from xalpha.record import record

class policy(record):
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
        times = pd.date_range(self.start,self.end)
        for date in times:
            action = self.status_gen(date)
            if action>0:
                datel.append(date)
                actionl.append(action)
            elif action<0:
                datel.append(date)
                actionl.append(action*0.005)
        df = pd.DataFrame(data={'date':datel, self.aim.code:actionl})
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

class scheduled_tune(scheduled):
    '''
    定期不定额的方式进行投资，基于点数分段进行投资
    '''
    def __init__(self, infoobj, totmoney, times, piece):
        '''
        :param piece: list of tuples, eg.[(1000,2),(2000,1.5)]. It means when the fund netvalue
            is small than some value, we choose to buy multiple times the totmoney. In this example,
            if the netvalue is larger than 2000, then no purchase happen at all.
        '''
        self.piece = piece
        super().__init__(infoobj, totmoney, times)

    def status_gen(self, date):
        if date in self.times:
            value = self.price[self.price['date']>=date].iloc[0].netvalue
            for term in self.piece:
                if value<=term[0]:
                    return term[1]*self.totmoney
            return 0
        else:
            return 0

class grid(policy):
    '''
    网格投资类，用于指导网格投资策略的生成和模拟。这一简单的网格，买入仓位基于均分总金额，每次的卖出仓位基于均分总份额。
    因此实际上每次卖出的份额都不到对应原来档位买入的份额，从而可能实现更多的收益。

    :param infoobj: info object, trading aim of the grid policy
    :param buypercent: list of positive int or float, the grid of points when purchasing, in the unit of percent
        比如 [5,5,5,5] 表示以 start 这天的价格为基准，每跌5%，就加一次仓，总共加四次仓
    :param sellpercent: list of positive int or float, the grid of points for selling
        比如 [8,8,8,8] 分别对应上面各买入仓位应该涨到的百分比从而决定卖出的点位，两个列表都是靠前的是高价位仓，两列表长度需一致
    :param start: date str of policy starting
    :param end: date str of policy ending
    :param totmoney: 总钱数，平均分给各个网格买入仓位
    '''
    def __init__(self, infoobj, buypercent, sellpercent, start, end=yesterdaydash, totmoney = 100000):
        assert len(buypercent) == len(sellpercent)
        self.division = len(buypercent)
        self.pos = 0
        self.zero = infoobj.price[infoobj.price['date']>=start].iloc[0].loc['netvalue']
        buypts = [self.zero]
        sellpts = []
        for term in buypercent:
            buypts.append(buypts[-1]*(1-term/100.))
        for i,term in enumerate(sellpercent):
            sellpts.append(buypts[i+1]*(1+term/100.))
        self.buypts = buypts[1:]
        self.sellpts = sellpts
        self.buypercent = buypercent
        self.sellpercent = sellpercent
        super().__init__(infoobj, start, end, totmoney)

    def status_gen(self,date):
        # 过滤交易日这一需求，交给各个类自由裁量，这里网格类就需要过掉非交易日干扰，
        # 而定投类中则不过掉，遇到非交易日顺延定投更合理些
        if date.strftime('%Y-%m-%d') not in opendate:
            return 0

        if date == self.start:
            if self.buypercent[0] == 0:
                self.pos += 1
                return myround(self.totmoney/self.division)
            else:
                return 0
        value = self.price[self.price['date']<=date].iloc[-1].loc['netvalue']
        valueb = self.price[self.price['date']<=date].iloc[-2].loc['netvalue']
        action = 0
        for i,buypt in enumerate(self.buypts):
            if (value-buypt)<=0 and (valueb-buypt)>0 and self.pos<=i:
                self.pos += 1
                action += myround(self.totmoney/self.division)
        for j,sellpt in enumerate(self.sellpts):
            if (value-sellpt)>=0 and (valueb-sellpt)<0 and self.pos>j:
                action += -1/self.pos
                self.pos += -1
        return action




