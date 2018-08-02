'''
module for status table IO
'''
import pandas as pd

class record():
	'''
	basic class for status table read in from csv file
	staus table 是关于对应基金的申赎寄账单，不同的行代表不同日期，不同的列代表不同基金，
	第一行各单元格分别为 date, 及基金代码。第一列各单元格分别为 date 及各个交易日期，形式 eg. 20170129
	表格内容中无交易可以直接为空或0，申购为正数，对应申购金额（申购费扣费前状态），赎回为负数，对应赎回份额，
	注意两者不同，恰好对应基金的金额申购份额赎回原则，记录精度均只完美支持一位小数。
	几个更具体的特殊标记：
	1. 小数点后第二位如果是5，且当日恰好为对应基金分红日，标志着选择了分红再投入的方式，否则默认分红拿现金
	2. 对于赎回的负数，如果是一个绝对值小于 0.005 的数，标记了赎回的份额占当时总份额的比例而非赎回的份额数目，
		其中0.005对应全部赎回，线性类推。eg. 0.001对应赎回20%。

	params path: string for the csv file path
	'''
	def __init__(self, path='input.csv'):
		df = pd.read_csv(path)
		df.date=[pd.Timestamp.strptime(str(int(df.iloc[i].date)),"%Y%m%d") for i in range(len(df))]
		df.fillna(0, inplace=True)
		self.status = df