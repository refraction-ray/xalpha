# -*- coding: utf-8 -*-
'''
module for trade class
'''
import datetime as dt
import pandas as pd
from pyecharts import Line
import xalpha.remain as rm
from xalpha.cons import convert_date, xirr, myround, yesterdayobj

def xirrcal(cftable, trades, date, guess):
	'''
	calculate the xirr rate

	:param cftable: cftable (pd.Dateframe) with date and cash column
	:param trades: list [trade1, ...], every item is an trade object, 
		whose shares would be sold out virtually
	:param date: string of date or datetime object, 
		the date when virtually all holding positions being sold
	:param guess: floating number, a guess at the xirr rate solution to be used 
		as a starting point for the numerical solution
	:returns: the IRR as a single floating number
	'''
	date = convert_date(date)
	partcftb = cftable[cftable['date']<=date]
	if len(partcftb) == 0:
		return 0
	cashflow = [(row['date'],row['cash']) for i, row in partcftb.iterrows()]
	rede = 0
	for fund in trades:
		rede += fund.aim.shuhui(fund.dailyreport(date).get('currentshare',0), date, fund.remtable[fund.remtable['date']<=date].iloc[-1].rem)[1]
	cashflow.append((date,rede))
	return xirr(cashflow, guess)

class trade():
	'''
	Trade class with fundinfo obj as input and its main attrs are cftable and remtable:
		
		1. cftable: pd.Dataframe, 现金流量表，每行为不同变更日期，三列分别为 date，cash， share，标记对于某个投资标的
		现金的进出和份额的变化情况，所有的份额数据为交易当时的不复权数据。基金份额折算通过流量表中一次性的份额增减体现。
		
		2. remtable：pd.Dataframe, 持仓情况表，每行为不同变更日期，两列分别为 date 和 rem， rem 数据结构是一个嵌套的列表，
		包含了不同时间买入仓位的剩余情况，详情参见 remain 模块。这一表格如非必需，避免任何直接调用。

	:param infoobj: info object as the trading aim
	:param status: status table, obtained from record class
	'''
	def __init__(self, infoobj, status):
		self.aim = infoobj
		code = self.aim.code
		self.cftable = pd.DataFrame([], columns=['date','cash','share'])
		self.remtable = pd.DataFrame([], columns=['date','rem'])
		self.status = status.loc[:,['date',code]]
		self._arrange()

	def _arrange(self):
		while (1):
			try:
				self._addrow()
			except Exception as e:
				if e.args[0]=='no other info to be add into cashflow table':
					break
				else:
					raise e
	
	def _addrow(self):
		'''
		Return cashflow table with one more line or raise an exception if there is no more line to add
		The same logic also applies to rem table
		关于对于一个基金多个操作存在于同一交易日的说明：无法处理历史买入第一笔同时是分红日的情形, 事实上也不存在这种情形。无法处理一日多笔买卖的情形。
		同一日既有卖也有买不现实，多笔买入只能在 csv 上合并记录，由此可能引起份额计算 0.01 的误差。可以处理分红日买入卖出的情形。
		分级份额折算日封闭无法买入，所以程序直接忽略当天的买卖。因此不会出现多个操作共存的情形。
		'''
		# the design on data remtable is disaster, it is very dangerous though works now

		code = self.aim.code
		if len(self.cftable) == 0:
			if len(self.status[self.status[code]!=0]) == 0:
				raise Exception("no other info to be add into cashflow table") 
			i = 0
			while (self.status.iloc[i].loc[code] == 0):
				i += 1
			value = self.status.iloc[i].loc[code]
			date = self.status.iloc[i].date
			if value>0:
				rdate, cash, share = self.aim.shengou(value, date)
				rem = rm.buy([], share, rdate)
			else: 
				raise Exception("You cannot sell first when you never buy")
		elif len(self.cftable) > 0:
			recorddate = list(self.status.date)
			lastdate = self.cftable.iloc[-1].date+pd.Timedelta(1, unit='d')
			while ((lastdate not in self.aim.specialdate) and ((lastdate not in recorddate)
															  or ((lastdate in recorddate) 
																  and (self.status[self.status['date']==lastdate].loc[:,code].any() == 0) ))):
				lastdate += pd.Timedelta(1, unit='d')
				if (lastdate - yesterdayobj).days>1:
					raise Exception("no other info to be add into cashflow table")
			date = lastdate
			label = 0
			cash = 0
			share = 0
			rem = self.remtable.iloc[-1].rem
			rdate = date

			if (date in recorddate) and (date not in self.aim.zhesuandate): 
	# deal with buy and sell and label the fenhongzaitouru, namely one label a 0.05 in the original table to label fenhongzaitouru
				value = self.status[self.status['date']==date].iloc[0].loc[code]
				fenhongmark = round(10*value-int(10*value),1)
				if fenhongmark==0.5:
					label = 1 # fenhong reinvest
					value = round(value, 1) 

				if value>0: # value stands for purchase money
					rdate, dcash, dshare = self.aim.shengou(value, date)
					rem = rm.buy(rem ,dshare, rdate)

				elif value< -0.005: # value stands for redemp share
					rdate, dcash, dshare = self.aim.shuhui(-value, date, self.remtable.iloc[-1].rem)
					_, rem = rm.sell(rem, -dshare, rdate)
				elif value>=-0.005 and value<0: 
					# value now stands for the ratio to be sold in terms of remain positions, -0.005 stand for sell 100%
					remainshare = sum(self.cftable.loc[:,'share'])
					ratio = -value/0.005
					rdate, dcash,dshare = self.aim.shuhui(remainshare*ratio, date, self.remtable.iloc[-1].rem)
					_, rem = rm.sell(rem, -dshare, rdate)
				else: # in case value=0, when specialday is in record day 
					rdate, dcash, dshare = date, 0,0
					
				cash += dcash
				share += dshare
			if date in self.aim.specialdate: # deal with fenhong and xiazhe
				comment = self.aim.price[self.aim.price['date']==date].iloc[0].loc['comment']
				if isinstance(comment,float):
					if comment<0:
						dcash2, dshare2 = 0, sum( [myround(sh*(-comment-1))  for _, sh in rem] ) # xiazhe are seperately carried out based on different purchase date
						rem = rm.trans(rem, -comment, date)
						#myround(sum(cftable.loc[:,'share'])*(-comment-1))
					elif comment>0 and label == 0:
						dcash2, dshare2 = myround(sum(self.cftable.loc[:,'share'])*comment), 0
						rem = rm.copy(rem)

					elif comment>0 and label == 1:
						dcash2, dshare2 = 0, myround(sum(self.cftable.loc[:,'share'])*
							(comment/self.aim.price[self.aim.price['date']==date].iloc[0].netvalue))
						rem = rm.buy(rem, dshare2, date)

					cash += dcash2
					share += dshare2
				else:
					raise Exception('comments not recoginized')


		self.cftable = self.cftable.append(pd.DataFrame([[rdate,cash,share]],columns=['date','cash','share']),ignore_index=True)
		self.remtable = self.remtable.append(pd.DataFrame([[rdate,rem]],columns=['date','rem']),ignore_index=True)


	def xirrrate(self, date=yesterdayobj, guess=0.1):
		'''
		give the xirr rate for all the trade of the aim before date (virtually sold out on date)

		:param date: string or obj of datetime, the virtually sell-all date 
		'''
		return xirrcal(self.cftable,[self], date, guess)
		
	def dailyreport(self, date=yesterdayobj):
		'''
		breif report dict of certain date status on the fund investment

		:param date: string or obj of date, show info of the date given
		:returns: empty dict if no share is remaining that date
			dict of various data on the trade positions
		'''
		date = convert_date(date)
		partcftb = self.cftable[self.cftable['date']<=date]
		totinput = myround(-sum(partcftb.loc[:,'cash']))
		value = self.aim.price[self.aim.price['date']<=date].iloc[-1].netvalue
		currentshare = myround(sum(partcftb.loc[:,'share']))
		currentcash = myround(currentshare*value)
		if currentshare == 0:
			return {}
		return {'date':date, 'unitvalue':value, 'currentvalue': currentcash, 'originalvalue': totinput, 
					'returnrate': round((currentcash/totinput-1)*100,4), 'currentshare': currentshare, 
					'unitcost': round(totinput/currentshare,4)}
	
	def v_tradecost(self,end=yesterdayobj,**vkwds):
		'''
		visualization giving the average cost line together with netvalue line

		:param vkwds: keywords options for line.add()
		:returns: pyecharts.line
		'''
		funddata = []
		costdata = []
		pprice = self.aim.price[self.aim.price['date']<=end]
		for i, row in pprice.iterrows():
			date = row['date']
			funddata.append( [date, row['netvalue']] )
			cost = self.dailyreport(date).get('unitcost',None)
			if cost is not None:
				costdata.append([date, cost])

		line=Line()
		line.add('fundvalue',[1 for _ in range(len(funddata))],funddata)
		line.add('average_cost',[1 for _ in range(len(costdata))],costdata,
				 is_datazoom_show = True,xaxis_type="time")

		return line
	
	def v_totvalue(self,end=yesterdayobj,**vkwds):
		'''
		visualization on the total values change of the aim 
		'''
		valuedata = []
		partp = self.aim.price[self.aim.price['date']>=self.cftable.iloc[0].date]
		partp = partp[partp['date']<=end]
		for i, row in partp.iterrows():
			date = row['date']
			valuedata.append( [date, self.dailyreport(date).get('currentvalue',0)] )
		
		line=Line()
		line.add('totvalue',[1 for _ in range(len(valuedata))],valuedata,
				 is_datazoom_show = True,xaxis_type="time")

		return line


	def __repr__(self):
		return self.aim.name+' 交易情况'
