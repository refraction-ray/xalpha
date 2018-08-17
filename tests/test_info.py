import sys
sys.path.insert(0, "../")
import xalpha as xa
import pandas as pd
import pytest

ca = xa.cashinfo(interest=0.0002, start='2015-01-01')
zzhb = xa.indexinfo('0000827')
hs300 = xa.fundinfo('000311')
zogqb = xa.mfundinfo('001211')

def test_cash():    
    assert round(ca.price[ca.price['date']=='2018-01-02'].iloc[0].netvalue,4) == 1.2453
    assert ca.code == 'mf'
    date, value, share = ca.shuhui(300,'2018-01-01', [[pd.Timestamp('2017-01-03'),200]])
    assert date == pd.Timestamp('2018-01-02')
    assert value == 249.06
    assert share == -200
    ca.bcmkset(ca)
    assert ca.alpha()== 0
    assert round(ca.total_annualized_returns('2018-01-01'),4) == 0.0757


def test_index():
	assert round(zzhb.price[zzhb.price['date']=='2012-02-01'].iloc[0].totvalue,3) == 961.406
	assert round(zzhb.price[zzhb.price['date']=='2015-02-02'].iloc[0].netvalue, 2) == 1.62
	assert zzhb.name == '中证环保'
	assert zzhb.shengou(100, '2018-01-02')[2]==55.24
	assert zzhb.shuhui(100,'2016-01-01', [[pd.Timestamp('2017-01-03'),200]])[2] == 0
	zzhb.info()
	zzhb.ma(window=10)
	zzhb.md()
	zzhb.ema(col='totvalue')
	zzhb.macd()
	zzhb.mtm()
	zzhb.roc()
	zzhb.boll()
	zzhb.bias()
	zzhb.rsi()
	zzhb.kdj()
	zzhb.wnr()
	zzhb.dma(col='totvalue')
	zzhb.bbi()
	zzhb.trix(col='totvalue')
	zzhb.psy()
	row = zzhb.price[zzhb.price['date']=='2018-08-01'].iloc[0]
	assert round(row['MD5'],3) == 0.012
	assert round(row['MA10'],3) == 1.361
	assert round(row['MACD_OSC_12_26'],4) ==0.0076
	assert round(row['EMA5'],1) == 1318.8
	assert round(row['MTM10'],4) == 0.0078
	assert round(row['ROC10'],4) == 0.0058
	assert round(row['BOLL_UPPER'],3) == 1.398
	assert round(row['BIAS10'],3) == -0.012
	assert round(row['RSI14'],3) == 0.411
	assert round(row['KDJ_J'],4) == 0.0456
	assert round(row['WNR14'],2) == 0.27
	assert round(row['AMA'],2) == -87.71
	assert round(row['BBI'],3) == 1.356
	assert round(row['TRIX10'],4) == 0.0005
	assert round(row['PSYMA12'],2) == 0.47
	zzhb.v_techindex(col=['TRIX10'])

def test_fund():
	assert hs300.label == 2
	assert hs300.name == '景顺长城沪深300增强' 
	assert hs300.fenhongdate[1]  == pd.Timestamp('2017-08-15')
	assert float(hs300.special[hs300.special['date']=='2017-08-04']['comment']) == 0.19
	hs300.rate = 0.12
	hs300.segment = [[0, 7], [7, 365], [365, 730], [730]]
	with pytest.raises(Exception) as excinfo:   
		hs300.shuhui(100, '2014-01-04',[[pd.Timestamp('2014-01-03'),200],[pd.Timestamp('2017-01-03'),200]])   
	assert str(excinfo.value) == 'One cannot move share before the lastest operation' 
	assert hs300.shuhui(320, '2018-01-01',[[pd.Timestamp('2011-01-03'),200],[pd.Timestamp('2017-12-29'),200]])[1] == 685.72
	assert hs300.shengou(200,'2018-07-20')[2] == 105.24
	hs300.info()

def test_mfundinfo():
	zogqb.bcmkset(xa.cashinfo())
	assert round(zogqb.total_annualized_returns('2018-08-01'),3) == 0.036

def test_evaluate():
	comp = xa.evaluate(ca,zzhb,hs300)
	comp.v_netvalue(end='2018-08-01')
	comp.v_correlation()
	comp2 = xa.evaluate(ca, zzhb, start='2018-01-01')
	assert round(comp2.correlation_table('2018-08-01').iloc[0,1],3)==0.064
