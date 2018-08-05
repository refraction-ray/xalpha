# -*- coding: utf-8 -*-
'''
module for mul and mulfix class: fund combination management
'''

import pandas as pd
from pyecharts import  Pie, ThemeRiver
from xalpha.trade import xirrcal, trade
from xalpha.indicator import indicator
from xalpha.info import cashinfo, fundinfo
from xalpha.cons import yesterdayobj, yesterdaydash, myround, convert_date






class mul():
	'''
	multiple fund positions manage class

	:param *fundtradeobj: list of trade obj which you want to analyse together
	:param status: the status table of trade, all code in this table would be considered
		one must provide one of the two paramters, if both are offered, status will be overlooked
	'''
	def __init__(self, *fundtradeobj, status=None):
		if not fundtradeobj: 
			# warning: not a very good way to atoumatic generate these fund obj
			# because there might be some funds use round_down for share calculation, ie, label=2 must be given
			# unless you are sure corresponding funds are added to the droplist
			fundtradeobj = []
			for code in status.columns[1:]:
				fundtradeobj.append(trade(fundinfo(code), status))
		self.fundtradeobj = tuple(fundtradeobj)
		self.totcftable = self._mergecftb()
	
	def tot(self, prop='currentvalue', date=yesterdayobj):
		'''
		sum of all the values from one prop of fund daily report, 
		of coures many of the props make no sense to sum
		
		:param prop: string defined in the daily report dict, 
			typical one is 'currentvalue' or 'originalvalue'
		'''
		res = 0
		for fund in self.fundtradeobj:
			res += fund.dailyreport(date).get(prop, 0)
		return res
	
	def combsummary(self, date=yesterdayobj):
		'''
		brief report table of every funds and the combination investment

		:param date: string or obj of date, show info of the date given
		:returns: empty dict if nothing is remaining that date
			dict of various data on the trade positions
		'''
		date = convert_date(date)
		name = []
		code = []
		cuva = []
		orva = []
		rera = []
		for fund in self.fundtradeobj:
			name.append(fund.aim.name)
			code.append(fund.aim.code)
			res = fund.dailyreport(date)
			cuva.append(res.get('currentvalue',0))
			orva.append(res.get('originalvalue',0))
			rera.append(res.get('returnrate',0))
		totcuva = sum(cuva)
		totorva = sum(orva)
		cuva.append(totcuva)
		orva.append(totorva)
		name.append('总计')
		code.append('xxxxxx')
		totrera = round((cuva[-1]/orva[-1]-1)*100,4)
		rera.append(totrera)
		df = pd.DataFrame(data={'基金名称':name,'基金代码':code,'基金现值':cuva,'基金成本':orva,'基金收益率':rera})
		return df

	def _mergecftb(self):
		'''
		merge the different cftable for different funds into one table
		'''
		dtlist = []
		for fund in self.fundtradeobj:
			dtlist2 = []
			for _,row in fund.cftable.iterrows():
				dtlist2.append((row['date'],row['cash']))
			dtlist.extend(dtlist2)

		nndtlist = set([item[0] for item in dtlist])
		nndtlist = sorted(list(nndtlist), key=lambda x: x)
		reslist = []
		for date in nndtlist:
			reslist.append(sum([item[1] for item in dtlist if item[0]==date]))
		df = pd.DataFrame(data={'date':nndtlist,'cash': reslist})
		df = df[df['cash']!=0]
		df = df.reset_index(drop=True)
		return df
	
	def xirrrate(self, date=yesterdayobj, guess=0.1):
		'''
		xirr rate evauation of the whole invest combination
		'''
		return xirrcal(self.totcftable, self.fundtradeobj, date, guess)


	def v_positions(self, date=yesterdayobj, **vkwds):
		'''
		pie chart visulization of positions ratio in combination
		'''
		sdata=sorted([(fob.aim.name,fob.dailyreport(date).get('currentvalue',0)) for fob in self.fundtradeobj],
					 key= lambda x:x[1], reverse=True)
		sdata1 = [item[0] for item in sdata ]
		sdata2 = [item[1] for item in sdata ]

		pie = Pie()
		pie.add("", sdata1, sdata2, legend_pos='left',legend_orient='vertical',**vkwds)
		return pie
	
	def v_positions_history(self, end=yesterdaydash, **vkwds):
		'''
		river chart visulization of positions ratio history
		use text size to avoid legend overlap in some sense, eg. legend_text_size=8
		'''
		start = self.totcftable.iloc[0].date
		times = pd.date_range(start, end)
		tdata = []
		for date in times:
			sdata=sorted([(date,fob.dailyreport(date).get('currentvalue',0),fob.aim.name) 
						  for fob in self.fundtradeobj], key= lambda x:x[1], reverse=True)
			tdata.extend(sdata)
		tr = ThemeRiver()
		tr.add([foj.aim.name for foj in self.fundtradeobj], tdata, is_datazoom_show=True,
			   is_label_show=False,legend_top="0%",legend_orient='horizontal', **vkwds)
		return tr

	def v_tradevolume(self, **vkwds):
		'''
		visualization on trade summary of the funds combination

		:param **vkwds: keyword argument for pyecharts Bar.add()
		:returns: pyecharts.bar
		'''
		return trade.vtradevolume(self.totcftable, **vkwds)


class mulfix(mul,indicator):
	'''
	introduce cash to make a closed investment system, where netvalue analysis can be applied
	namely the totcftable only has one row at the very beginning

	:param fundtradeobj: trade obj to be include
	:param status: status table,  if no trade obj is provided, it will include all fund 
		based on code in status table
	:param totmoney: positive float, the total money as the input at the beginning
	:param cashobj: cashinfo object, which is designed to balance the cash in and out
	'''
	def __init__(self, *fundtradeobj, status = None, totmoney = 100000, cashobj = None):
		super().__init__(*fundtradeobj, status=status)
		if cashobj is None:
			cashobj = cashinfo()
		self.totmoney = totmoney
		nst = mulfix._vcash(totmoney, self.totcftable, cashobj)
		cashtrade = trade(cashobj, nst)
#		 super().__init__(*self.fundtradeobj, cashtrade)
		self.fundtradeobj = list(self.fundtradeobj)
		self.fundtradeobj.append(cashtrade)
		self.fundtradeobj = tuple(self.fundtradeobj)
		inputl = [-sum(self.totcftable.iloc[:i].cash) for i in range(1,len(self.totcftable)+1)]
		if max(inputl)>totmoney:
			raise Exception('the initial total cash is too low')
		self.totcftable = pd.DataFrame(data={'date': [nst.iloc[0].date], 'cash':[-totmoney]})
		

	def _vcash(totmoney, totcftable, cashobj):
		'''
		return a virtue status table with a mf(cash) column based on the given tot money and cftable
		'''
		cashl = []
		cashl.append(totmoney+totcftable.iloc[0].cash)
		for i in range(len(totcftable)-1):
			date = totcftable.iloc[i+1].date
			delta = totcftable.iloc[i+1].cash
			if delta <0:
				cashl.append(myround(delta/cashobj.price[cashobj.price['date']<=date].iloc[-1].netvalue))
			else:
				cashl.append(delta)
		datadict = {'date':totcftable.loc[:,'date'],'mf':cashl}
		return pd.DataFrame(data=datadict)

	
	def dailyreport(self, date=yesterdayobj):
		'''
		daily info brief review based on the investment combination
		'''
		date = convert_date(date)
		currentcash = self.tot('currentvalue',date)
		value = currentcash/self.totmoney
		return {'date':date, 'unitvalue': value,'currentvalue': currentcash, 'originalvalue':self.totmoney,
			   'returnrate': round((currentcash/self.totmoney-1)*100,4), 
					'currentshare':self.totmoney, 'unitcost': 1.00}