# -*- coding: utf-8 -*-
'''

'''
from re import match
import datetime as dt
from xalpha.info import _download


class rtdata():
	'''
	get real time data of specific funds

	:param code: string of six digitals for funds
	'''
	def __init__(self, code):
		url = 'http://fundgz.1234567.com.cn/js/'+code+'.js'
		page = _download(url)
		self.code = code
		self.rtvalue = float(match(r'.*"gsz":"(\d*\.\d*)",.*',page.text)[1])
		self.name = match(r'.*"name":"([^,]*)",.*',page.text)[1]
		self.time = dt.datetime.strptime(match(r'.*"gztime":"([\d\s\-\:]*)".*',page.text)[1],'%Y-%m-%d %H:%M')



class review():
	'''
	scan whether there are fund status should be warned

	:param confs: eg. `conf = [{'plan':'grid',code':'100032','type':'low','condition':'1.03','date':'2018-08-03'},
		{'code':'100032','type':'high','condition': 1.022},{'code':'100032','date':'2018-08-03','suggestion':1000}]`
	'''
	def __init__(self, confs):
		self.confs = confs
		message = []
		for fund in self.confs:
			fundrt = rtdata(fund['code'])
			date = fund.get('date',None)
			suggestion = fund.get('suggestion',None)
			plan = fund.get('plan', None)
			condition1 = (fund.get('type',None) == 'low' and fundrt.rtvalue<fund.get('condition',0))
			condition2 = (fund.get('type',None) == 'high' and fundrt.rtvalue>fund.get('condition',1e6))
			
			idn = '%s(%s)实时净值为%s，'%(fundrt.name,fundrt.code,fundrt.rtvalue)
			if fund.get('type',None) is not None: 
				if condition1:
					loh = '低'
					val = '净值已%s于%s，'%(loh,fund['condition'])
				elif condition2:
					loh = '高'
					val = '净值已%s于%s，'%(loh,fund['condition'])
				else:
					val = ''
			else:
				val = '净值允许交易，'
			if date is not None:
				if fundrt.time.date() == dt.datetime.strptime(fund['date'],'%Y-%m-%d').date():
					dateinfo = '今日%s，满足日期限制，'%date
				else:
					dateinfo = ''
			else:
				dateinfo = '今日允许交易，'
			if suggestion is not None:
				if suggestion>0:
					sug = '建议买入%s元'%suggestion
				elif suggestion<0:
					sug = '建议买出全部份额的%s%%'%suggestion
			else:
				sug = '建议进行交易'
			if plan is not None:
				orig = '，来自%s计划的提醒'%plan
			else:
				orig = ''
			if len(val)!=0 and len(dateinfo)!=0:
				message.append(idn+val+dateinfo+sug+orig)

		self.message = message