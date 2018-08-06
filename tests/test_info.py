import sys
sys.path.insert(0, "../")
import xalpha as xa
import pandas as pd
import pytest

def test_cash():
    ca = xa.cashinfo(interest=0.0002, start='2015-01-01')
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
	zzhb = xa.indexinfo('0000827')
	assert round(zzhb.price[zzhb.price['date']=='2012-02-01'].iloc[0].totvalue,3) == 961.406
	assert round(zzhb.price[zzhb.price['date']=='2015-02-02'].iloc[0].netvalue, 2) == 1.62
	assert zzhb.name == '中证环保'
	assert zzhb.shengou(100, '2018-01-02')[2]==55.24
	assert zzhb.shuhui(100,'2016-01-01', [[pd.Timestamp('2017-01-03'),200]])[2] == 0
	zzhb.info()

def test_fund():
	hs300 = xa.fundinfo('000311')
	assert hs300.label == 2
	assert hs300.name == '景顺长城沪深300增强' 
	assert hs300.fenhongdate[1]  == pd.Timestamp('2017-08-15')
	hs300.rate = 0.12
	hs300.segment = [[0, 7], [7, 365], [365, 730], [730]]
	with pytest.raises(Exception) as excinfo:   
		hs300.shuhui(100, '2014-01-04',[[pd.Timestamp('2014-01-03'),200],[pd.Timestamp('2017-01-03'),200]])   
	assert str(excinfo.value) == 'One cannot move share before the lastest operation' 
	assert hs300.shuhui(320, '2018-01-01',[[pd.Timestamp('2011-01-03'),200],[pd.Timestamp('2017-12-29'),200]])[1] == 685.72
	assert hs300.shengou(200,'2018-07-20')[2] == 105.24
