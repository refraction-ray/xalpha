# -*- coding: utf-8 -*-
'''
module for implementation of indicator class, which is designed as MinIn for systems with netvalues
'''

import pandas as pd
from pyecharts import Line

from xalpha.cons import yesterdayobj, opendate

class indicator():
	'''
	MixIn class provide quant indicator tool box which is desinged as interface for mulfix class as well
	as info class, who are both treated as a single fund with price table of net value.
	Most of the quant indexes, their name conventions, definitions and calculations are from 
	`joinquant <https://www.joinquant.com/help/api/help?name=api#%E9%A3%8E%E9%99%A9%E6%8C%87%E6%A0%87>`_.
	Make sure first run obj.bcmkset() before you want to use functions in this class.
	'''
	def bcmkset(self, infoobj, start=None, riskfree = 0.0371724):
		'''
		Once you want to utilize the indicator tool box for analysis, first run bcmkset function to set
		the benchmark, otherwise most of the functions would raise error.
		:param infoobj: info obj, whose netvalue are used as benchmark
		:param start: datetime obj, indicating the starting date of all analysis.
			Note if use default start, there may be problems for some fundinfo obj, as lots of 
			funds lack netvalues of several days from our API, resulting unequal length between
			benchmarks and fund net values.
		:param riskfree: float, annual rate in the unit of 100%, strongly suggest make this value 
			consistent with the interest parameter when instanciate cashinfo() class
		'''
		self._pricegenerate()
		if start is None:
			self.start = self.price.iloc[0].date
		elif isinstance(start, str):
			self.start = pd.Timestamp.strptime(start,'%Y-%m-%d')
		self.benchmark = infoobj
		
		self.riskfree = riskfree
		self.bmprice = self.benchmark.price[self.benchmark.price['date']>=self.start]
		self.price = self.price[self.price['date']>=self.start]
		
	def _pricegenerate(self):
		'''
		generate price table for mulfix class, the cinfo class has this attr by default
		'''
		if getattr(self, 'price', None) is None:
			times = pd.date_range(self.totcftable.iloc[0].date, yesterdayobj)
			netvalue = []
			for date in times:
				netvalue.append(self.unitvalue(date))
			self.price = pd.DataFrame(data={'date':times, 'netvalue': netvalue})
			self.price = self.price[self.price['date'].isin(opendate)]
		
	def comparison(self, date=yesterdayobj):
		'''
		:returns: tuple of two pd.Dataframe, the first is for aim and the second if for the benchmark index
		all netvalues are normalized and set equal 1.00 on the self.start date
		'''
		partp = self.price[self.price['date']<=date]
		partm = self.bmprice[self.bmprice['date']<=date]
		normp = partp.iloc[0].netvalue
		normm = partm.iloc[0].netvalue
		partp['netvalue'] = partp['netvalue']/normp
		partm['netvalue'] = partm['netvalue']/normm
		return (partp, partm)
	
	def total_return(self, date=yesterdayobj):
		return round((self.price[self.price['date']<=date].iloc[-1].netvalue-self.price.iloc[0].netvalue)
					 /self.price.iloc[0].netvalue,4)
	
	def annualized_returns(price, start, date=yesterdayobj):
		'''
		:param price: price table of info().price
		:param start: datetime obj for starting date of calculation
		:param date: datetime obj for ending date of calculation
		'''
		datediff = (price[price['date']<=date].iloc[-1].date-start).days
		totreturn = (price[price['date']<=date].iloc[-1].netvalue-price.iloc[0].netvalue)/price.iloc[0].netvalue
		return round((1+totreturn)**(365/datediff)-1,4)
		
	def total_annualized_returns(self, date=yesterdayobj):
		return indicator.annualized_returns(self.price,self.start, date)

	def benchmark_annualized_returns(self, date=yesterdayobj):
		return indicator.annualized_returns(self.bmprice,self.start, date)
	
	def beta(self, date=yesterdayobj):
		bcmk = indicator.ratedaily(self.bmprice, date)
		bt = indicator.ratedaily(self.price, date)
		df = pd.DataFrame(data={'bcmk': bcmk,'bt': bt })
		res=df.cov()
		return res.loc['bcmk','bt']/res.loc['bcmk','bcmk']
	
	def alpha(self, date=yesterdayobj):
		rp = self.total_annualized_returns(date)
		rm = self.benchmark_annualized_returns(date)
		beta = self.beta(date)
		return rp-(self.riskfree+beta*(rm-self.riskfree))
	
	def correlation_coefficient(self, date=yesterdayobj):
		'''
		correlation coefficient between aim and benchmark values,
			可以很好地衡量指数基金的追踪效果

		:returns: float between -1 and 1
		'''
		bcmk = indicator.ratedaily(self.bmprice, date)
		bt = indicator.ratedaily(self.price, date)
		df = pd.DataFrame(data={'bcmk': bcmk,'bt': bt })
		res=df.cov()
		return res.loc['bcmk','bt']/((res.loc['bcmk','bcmk']**0.5)*res.loc['bt','bt']**0.5)   
	
	def ratedaily(price, date=yesterdayobj):
		partp = price[price['date']<=date]
		return [(partp.iloc[i+1].netvalue-partp.iloc[i].netvalue) /
					partp.iloc[i].netvalue for i in range(len(partp)-1)]
		
	def volatility(price, date=yesterdayobj):
		df = pd.DataFrame(data={'rate':indicator.ratedaily(price, date)})
		return df.std().rate*15.8144
	
	def algorithm_volatility(self, date=yesterdayobj):
		return indicator.volatility(self.price, date)
	
	def benchmark_volatility(self, date=yesterdayobj):
		return indicator.volatility(self.bmprice, date)
	
	def sharpe(self, date=yesterdayobj):
		rp = self.total_annualized_returns(date)
		return (rp-self.riskfree)/self.algorithm_volatility(date)
	
	def information_ratio(self, date=yesterdayobj):
		rp = self.total_annualized_returns(date)
		rm = self.benchmark_annualized_returns(date)
		vp = indicator.ratedaily(self.price, date)
		vm = indicator.ratedaily(self.bmprice, date)
		diff = [vp[i]-vm[i] for i in range(len(vm))]
		df = pd.DataFrame(data={'rate':diff})
		var = df.std().rate
		var = var*15.8144
		return (rp-rm)/var
	
	def max_drawdown(self, date=yesterdayobj):
		li = [(row['date'], row['netvalue']) for i,row in self.price[self.price['date']<=date].iterrows()]
		res = []
		for i, _ in enumerate(li):
			for j in range(i+1, len(li)):
				res.append((li[i][0],li[j][0],(li[j][1]-li[i][1])/li[i][1]))
		return min(res, key=lambda x:x[2])
	
	def v_netvalue(self, end=yesterdayobj, benchmark = True, **vkwds):
		'''
		visulaization on  netvalue curve
		
		:param vkwds: parameters for the pyecharts options in line.add(), eg. yaxis_min=0.7
		'''
		a, b = self.comparison(end)
		xdata = [1 for _ in range(len(a))]
		ydata = [[row['date'],row['netvalue']] for i, row in a.iterrows()]
		ydata2 = [[row['date'],row['netvalue']] for i, row in b.iterrows()]
		line=Line()
		line.add('algorithm',xdata,ydata,is_datazoom_show = True,xaxis_type="time",**vkwds)
		if benchmark is True:
			line.add('benchmark',xdata,ydata2,is_datazoom_show = True,xaxis_type="time",**vkwds)
		return line
