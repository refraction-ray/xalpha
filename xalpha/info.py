# -*- coding: utf-8 -*-
'''
modules of info class, including cashinfo, indexinfo and fundinfo class
'''
import re
import datetime as dt
import pandas as pd

from slimit import ast
from slimit.parser import Parser
from slimit.visitors import nodevisitor
import csv
import requests as rq
from bs4 import BeautifulSoup

from xalpha.cons import myround, convert_date, opendate, droplist, yesterday, yesterdaydash
import xalpha.remain as rm
from xalpha.indicator import indicator


def _download(url, tries=3):
	for count in range(tries):
		try:
			page = rq.get(url)
			break
		except (ConnectionResetError,rq.exceptions.RequestException) as e:
			if count == tries-1:
				raise e
	return page


def _shengoucal(sg, sgf, value, label):
	'''
	Infer the share of buying fund by money input, the rate of fee in the unit of %, 
		and netvalue of fund

	:param sg: positive float, 申购金额
	:param sgf: positive float, 申购费，以％为单位，如 0.15 表示 0.15%
	:param value: positive float, 对应产品的单位净值
	:param label: integer, 1 代表份额正常进行四舍五入， 2 代表份额直接舍去小数点两位之后。金额部分都是四舍五入
	:returns: tuple of two positive float, 净申购金额和申购份额
	'''
	jsg = myround(sg/(1+sgf*1e-2))
	share = myround(jsg/value, label)
	return (jsg, share)


def _nfloat(string):
	'''
	deal with comment column in fundinfo price table, 
	positive value for fenhong and negative value for chaifen, 
	keep other unrocognized pattern as original string
	'''
	result = 0
	if string != '""':
		try:
			result = float(string)
		except ValueError:
			if re.match(r'"分红\D*(\d*\.\d*)\D*"',string):
				result = float(re.match(r'"分红\D*(\d*\.\d*)\D*"',string).group(1))
			elif re.match(r'"拆分\D*(\d*\.\d*)\D*"',string):
				result = -float(re.match(r'"拆分\D*(\d*\.\d*)\D*"',string).group(1))
			else:
				result = string
	return result



class basicinfo(indicator):
	'''
	Base class for info of fund, index or even cash, 
	which cannot be directly instantiate, the basic implementation consider 
	redemption fee as zero when shuhui() function is implemented

	:param code: string of code for specific product
	'''
	def __init__(self, code):
		self.code = code
		self.label = 1
		self.specialdate = []
		self.fenhongdate = []
		self.zhesuandate = []
		self._basic_init() # update self. name rate and price table

	def _basic_init(self):
		'''
		set self. name rate and price (dataframe) as well as other necessary attr of info()
		'''
		# below lines are just showcase, this function must be rewrite by child classes
		# self.name = 'unknown'
		# self.rate = 0
		# self.price = pd.DataFrame(data={'date':[],'netvalue':[],'comment':[]})
		raise NotImplementedError
		
	def shengou(self, value, date):
		'''
		give the realdate deltacash deltashare tuple based on purchase date and purchase amount
		
		:returns: three elements tuple, the first is the actual dateobj of commit
			the second is a negative float for cashin, 
			the third is a positive float for share increase
		'''
		row = self.price[self.price['date']>=date].iloc[0]
		share = _shengoucal(value, self.rate, row.netvalue , label = self.label)[1]
		return (row.date, -myround(value), share)
			
	def shuhui(self, share, date, rem):
		'''
		give the cashout considering redemption rates as zero
		
		:returns: three elements tuple, the first is dateobj
		the second is a positive float for cashout, 
		the third is a negative float for share decrease
		'''
		date = convert_date(date)
		tots = sum([remitem[1] for remitem in rem if remitem[0]<=date])
		if share> tots:
			sh = tots
		else:
			sh = share
		row = self.price[self.price['date']>=date].iloc[0]
		value = myround(sh*row.netvalue)
		return (row.date, value, -myround(sh))
	
	def info(self):
		'''
		print basic info on the class
		'''
		print("fund name: %s" %self.name)
		print("fund code: %s" %self.code)
		print("fund purchase fee: %s%%" %self.rate)
	
	def __repr__(self):
		return self.name
   



class fundinfo(basicinfo):
	'''
	class for specific fund with basic info and every day values 
	所获得的基金净值数据一般截止到昨日。但注意QDII基金的净值数据会截止的更早，因此部分时间默认昨日的函数可能出现问题，
	处理QDII基金时，需要额外注意。

	:param code: str, 基金六位代码字符
	:param label: integer 1 or 2, 取2表示基金申购时份额直接舍掉小数点两位之后。当基金处于 cons.droplist 名单中时，
		label 总会被自动设置为2。非名单内基金可以显式令 label=2.
	'''
	def __init__(self, code, label = 1):
		self.url = 'http://fund.eastmoney.com/pingzhongdata/'+code+'.js' # js url api for info of certain fund
		self.feeurl = 'http://fund.eastmoney.com/f10/jjfl_'+code+'.html' # html url for trade fees info of certain fund
		self.page = _download(self.url)
		self._feepreprocess()
		super().__init__(code)
		if label == 2 or (code in droplist):
			self.label = 2 # the scheme of round down on share purchase
		else :
			self.label = 1
		self.special = self.price[self.price['comment']!=0]
		self.specialdate = list(self.special['date']) 
		# date with nonvanishing comment, usually fenhong or zhesuan
		try:
			self.fenhongdate = list(self.price[self.price['comment']>0]['date'])
			self.zhesuandate = list(self.price[self.price['comment']<0]['date'])
		except TypeError:
			print('There are still string comments for the fund!')


	def _basic_init(self):
		parser = Parser() # parse the js text of API page using slimit module
		tree = parser.parse(self.page.text)
		nodenet = [node.children()[0].children()[1] for node in nodevisitor.visit(tree)
			if isinstance(node, ast.VarStatement) and node.children()[0].children()[0].value=='Data_netWorthTrend'][0]
		nodetot = [node.children()[0].children()[1] for node in nodevisitor.visit(tree)
			if isinstance(node, ast.VarStatement) and node.children()[0].children()[0].value=='Data_ACWorthTrend'][0]
		## timestamp transform tzinfo must be taken into consideration
		tz_bj = dt.timezone(dt.timedelta(hours=8))

		infodict = {"date":[dt.datetime.fromtimestamp(int(nodenet.children()[i].children()[0].right.value)/1e3, tz=tz_bj).replace(tzinfo=None) 
					 for i in range(len(nodenet.children()))],
			  "netvalue":[float(nodenet.children()[i].children()[1].right.value) for i in range(len(nodenet.children()))],
			  "comment": [_nfloat(nodenet.children()[i].children()[3].right.value) for i in range(len(nodenet.children()))],
			  "totvalue": [float(nodetot.children()[i].children()[1].value) for i in range(len(nodenet.children()))]}
		
		rate = [node.children()[0].children()[1] for node in nodevisitor.visit(tree) 
			  if isinstance(node, ast.VarStatement) and (node.children()[0].children()[0].value=='fund_Rate')][0]
		
		name = [node.children()[0].children()[1] for node in nodevisitor.visit(tree) 
			  if isinstance(node, ast.VarStatement) and (node.children()[0].children()[0].value=='fS_name')][0]
		
		self.rate = float(rate.value.strip('"')) # shengou rate in tiantianjijin, daeshengou rate discount is not considered
		self.name = name.value.strip('"') # the name of the fund
		df = pd.DataFrame(data=infodict)
		df = df[df['date'].isin(opendate)] 
		df = df.reset_index(drop=True)
		self.price = df
		
	def _feepreprocess(self):
		'''
		Preprocess to add self.feeinfo and self.segment attr according to redemption fee info
		'''
		feepage = _download(self.feeurl)
		soup = BeautifulSoup(feepage.text,"lxml") # parse the redemption fee html page with beautiful soup
		self.feeinfo = [item.string for item in soup.findAll("a", {"name":"shfl"})[0].parent.parent.next_sibling.next_sibling.find_all("td") if item.string!="---"]
		self.segment = fundinfo._piecewise(self.feeinfo)

	def _piecewise(a):
		'''
		Transform the words list into a pure number segment list for redemption fee, eg. [[0,7],[7,365],[365]]
		'''
		b = [(a[2*i].replace("小于","").replace("大于","").replace("等于","").replace("个","")).split("，") for i in range(int(len(a)/2))]
		for j, tem in enumerate(b):
			for i, num in enumerate(tem):
				if num[-1]=="天":
					num = int(num[:-1])
				elif num[-1]=="月":
					num = int(num[:-1])*30
				else:
					num = int(num[:-1])*365
				b[j][i] = num
		b[0].insert(0,0)
		for i in range(len(b)-1):
			if b[i][1]-b[i+1][0] == -1:
				b[i][1] = b[i+1][0]
			elif b[i][1]==b[i+1][0]:
				pass
			else:
				print('Something weird on redem fee, please adjust self.segment by hand')
			  
		return b
	
	def feedecision(self, day):
		'''
		give the redemption rate in percent unit based on the days difference between purchase and redemption
		
		:param day: integer， 赎回与申购时间之差的自然日数
		:returns: float，赎回费率，以％为单位
		'''
		i=-1
		for seg in self.segment:
			i+=2
			if day-seg[0]>=0 and (len(seg)==1 or day-seg[-1]<0):
				return float(self.feeinfo[i].strip("%")) 
		return 0 # error backup, in case there is sth wrong in segment

	def shuhui(self, share, date, rem):
		'''
		give the cashout based on rem term considering redemption rates
		
		:returns: three elements tuple, the first is dateobj
		the second is a positive float for cashout, 
		the third is a negative float for share decrease
		'''
#		 value = myround(share*self.price[self.price['date']==date].iloc[0].netvalue)
		date = convert_date(date)
		row = self.price[self.price['date']>=date].iloc[0]
		soldrem, _ = rm.sell(rem, share, row.date)
		value = 0
		sh = myround(sum([item[1] for item in soldrem]))
		for d,s in soldrem:
			value += myround(s*row.netvalue*(1-self.feedecision((row.date-d).days)*1e-2))
		return (row.date, value ,-sh)
	
	def info(self):
		super().info()
		print("fund redemption fee info: %s" %self.feeinfo)


class indexinfo(basicinfo):
	'''
	Get everyday close price of specific index.
	In self.price table, totvalue column is the real index 
	while netvalue comlumn is normalized to 1 for the start date.
	In principle, this class can also be used to save stock prices but the price is without adjusted.

	:param code: string with seven digitals! note the code here has an extra digit at the beginning,
		0 for sh and 1 for sz. 
	'''
	def __init__(self, code):
		date = yesterday
		self.url = 'http://quotes.money.163.com/service/chddata.html?code='+code+'&start=19901219&end='+date+'&fields=TCLOSE'
		super().__init__(code)
		
	def _basic_init(self):
		raw = _download(self.url)
		cr = csv.reader(raw.text.splitlines(), delimiter=',')
		my_list = list(cr)
		factor = float(my_list[-1][3])
		dd = {'date': [dt.datetime.strptime(my_list[i+1][0],'%Y-%m-%d') for i in range(len(my_list)-1)], 
			 'netvalue': [float(my_list[i+1][3])/factor for i in range(len(my_list)-1)],
			 'totvalue':[float(my_list[i+1][3]) for i in range(len(my_list)-1)],
			 'comment': [0 for _ in range(len(my_list)-1)]} 
		index = pd.DataFrame(data=dd)
		index = index.iloc[::-1]
		index = index.reset_index(drop=True)
		self.price = index[index['date'].isin(opendate)]
		self.name = my_list[-1][2]
		self.rate = 0
	

class cashinfo(basicinfo):
	'''
	A virtual class for remaining cash manage: behave like monetary fund
	
	:param interest: float, daily rate in the unit of 100%, note this is not a year return rate!
	:param start: str of date or dateobj, the virtual starting date of the cash fund
	'''
	def __init__(self, interest=0.0001, start='2012-01-01'):
		self.interest = interest
		start = convert_date(start)
		self.start = start
		super().__init__('mf')
		
	def _basic_init(self):
		self.name = "货币基金"
		self.rate = 0
		datel = list(pd.date_range(dt.datetime.strftime(self.start,'%Y-%m-%d'),yesterdaydash))
		valuel = []
		for i,date in enumerate(datel):
			valuel.append((1+self.interest)**i)
		dfdict = {'date': datel, 'netvalue':valuel, 'totvalue':valuel,'comment': [0 for _ in datel]}
		df = pd.DataFrame(data=dfdict)
		self.price = df[df['date'].isin(opendate)]
