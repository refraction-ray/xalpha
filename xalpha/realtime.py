# -*- coding: utf-8 -*-
'''

'''
from re import match
import datetime as dt
import pandas as pd
from xalpha.info import _download, fundinfo
from xalpha.cons import today
from xalpha.trade import trade



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


def rfundinfo(code):
	'''
	give a fundinfo object with todays estimate netvalue at running time

	:param code: string of six digitals for funds
	:returns: the fundinfo object
	'''
	fundobj = fundinfo(code)
	rt = rtdata(code)
	rtdate = dt.datetime.combine(rt.time, dt.time.min)
	rtvalue = rt.rtvalue
	if (rtdate-fundobj.price.iloc[-1].date).days > 0:
		fundobj.price = fundobj.price.append(pd.DataFrame([[rtdate,rtvalue,fundobj.price.iloc[-1].totvalue,0]],
			columns=['date','netvalue','totvalue','comment']),ignore_index=True)
	return fundobj

class review():
	'''
	review policys and give the realtime purchase suggestions

	:param policylist: list of policy object
	:param namelist: list of names of corresponding policy, default as 0 to n-1
	:param date: object of datetime, check date, today is prefered, date other than is not guaranteed
	'''
	def __init__(self, policylist, namelist=None, date=today):
		self.warn = []
		self.message = []
		self.policylist = policylist
		if namelist is None:
			self.namelist = [i for i in range(len(policylist))]
		else:
			self.namelist = namelist
		assert len(self.policylist) == len(self.namelist)
		for i,policy in enumerate(policylist):
			row = policy.status[policy.status['date']==date]
			if len(row) == 1:
				warn = (policy.aim.name, policy.aim.code, 
					row.iloc[0].loc[policy.aim.code], self.namelist[i])
				self.warn.append(warn)
				if warn[2]>0:
					sug = '买入%s元'%warn[2]
				elif warn[2]<0:
					share = trade(fundinfo(warn[1]),policy.status).briefdailyreport().get('currentshare',0)
					share = -warn[2]/0.005* share
					sug = '卖出%s份额'%share
				self.message.append('根据%s计划，建议%s，%s(%s)'%(warn[3],sug,warn[0],warn[1]))

		
	def __str__(self):
		message = '\n'.join(map(str, self.message)) 
		return message
	
	def notification(self, conf):
		'''
		send email of self.message
		'''
		pass



