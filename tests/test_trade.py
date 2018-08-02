import sys
sys.path.insert(0, "../")
import xalpha as xa
import pytest

path = 'demo.csv'
cm = xa.fundinfo('164818')
cm_t = xa.trade(cm, xa.record(path).status)

def test_trade():
	assert cm_t.cftable.loc[2,'share'] == -129.14
	assert round(cm_t.xirrrate('2018-03-03'),3)== -0.24
	assert cm_t.dailyreport('2018-07-29')['unitcost'] == 1.346

def test_mul():
	with pytest.raises(Exception) as excinfo:   
		cm_m = xa.mulfix(cm_t, totmoney=200)
	assert str(excinfo.value) == 'You cannot sell first when you never buy'
	cm_m = xa.mulfix(cm_t, totmoney=500)
	cm_m.bcmkset(xa.indexinfo('1399971'),start='2016-09-28')
	assert round(cm_m.xirrrate('2018-07-29'),3) == -0.129
	assert round(cm_m.sharpe('2018-07-30'),3) == -1.734

def test_policy():
	allin = xa.policy.buyandhold(cm, '2015-06-01')
	cm_t2 = xa.trade(cm,allin.status)
	cm_m2=xa.mulfix(cm_t2)
	cm_m2.bcmkset(xa.indexinfo('1399971'))
	assert round(cm_m2.correlation_coefficient('2018-07-01'),3) == 0.980
	assert round(cm_m2.information_ratio('2016-07-01'),3) == -0.385
