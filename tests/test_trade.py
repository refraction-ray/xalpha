import sys
sys.path.insert(0, "../")
import xalpha as xa
import pytest

path = 'demo.csv'
cm = xa.fundinfo('164818')
statb = xa.record(path).status
cm_t = xa.trade(cm, statb)

def test_trade():
	assert cm_t.cftable.loc[2,'share'] == -129.14
	assert round(cm_t.xirrrate('2018-03-03'),3)== -0.24
	assert cm_t.dailyreport('2018-07-29')['unitcost'] == 1.346

def test_mul():
	with pytest.raises(Exception) as excinfo:   
		cm_m = xa.mulfix(cm_t, totmoney=200)
	assert str(excinfo.value) == 'You cannot sell first when you never buy'
	with pytest.raises(Exception) as excinfo:   
		cm_m = xa.mulfix(cm_t, totmoney=300)
	assert str(excinfo.value) == 'the initial total cash is too low'

	cm_m = xa.mulfix(cm_t, totmoney=500)
	cm_m.bcmkset(xa.indexinfo('1399971'),start='2016-09-28')
	assert round(cm_m.xirrrate('2018-07-29'),3) == -0.129
	assert round(cm_m.sharpe('2018-07-30'),3) == -1.734
	assert round(cm_m.v_netvalue().options['series'][0]['data'][1][1],4) == 1.0015
	assert round(cm_m.total_return('2018-07-01'),3) == -0.209
	assert round(cm_m.benchmark_volatility('2018-07-22'),3) == 0.192
	assert round(cm_m.max_drawdown('2018-08-01')[2],2) == -0.24

def test_mulfix():
	tot = xa.mulfix(status=statb,totmoney= 5000)
	assert tot.v_positions().options['legend'][0]['data'][1]=='富国中证红利指数增强'
	assert tot.v_positions_history().options['legend'][0]['data'][1]=='广发中债7-10年国开债指数A'

def test_policy():
	allin = xa.policy.buyandhold(cm, '2015-06-01')
	cm_t2 = xa.trade(cm,allin.status)
	cm_m2 = xa.mulfix(cm_t2)
	cm_m2.bcmkset(xa.indexinfo('1399971'))
	assert round(cm_m2.correlation_coefficient('2018-07-01'),3) == 0.980
	assert round(cm_m2.information_ratio('2016-07-01'),3) == -0.385
