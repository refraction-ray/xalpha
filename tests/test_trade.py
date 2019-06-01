import sys
sys.path.insert(0, "../")
import xalpha as xa
import pytest
import pandas as pd


path = 'demo.csv'
path1 = 'demo1.csv'
cm = xa.fundinfo('164818')
statb = xa.record(path).status
statl = xa.record(path1, format="list").status
cm_t = xa.trade(cm, statb)
ioconf = {'save': True, 'fetch': True, 'path': 'pytest', 'form': 'csv'}


def test_trade():
    assert cm_t.cftable.loc[2, 'share'] == -129.14
    assert round(cm_t.xirrrate('2018-03-03'), 3) == -0.24
    assert cm_t.dailyreport('2018-07-29').iloc[0]['单位成本'] == 1.346
    cm_t.v_tradecost('2018-08-01')
    cm_t.v_totvalue('2018-07-31')
    cm_t.v_tradevolume(freq='M')


def test_mul():
    with pytest.raises(Exception) as excinfo:
        cm_m = xa.mulfix(cm_t, totmoney=200)
    assert str(excinfo.value) == 'You cannot sell first when you never buy'
    with pytest.raises(Exception) as excinfo:
        cm_m = xa.mulfix(cm_t, totmoney=300)
    assert str(excinfo.value) == 'the initial total cash is too low'

    cm_m = xa.mulfix(cm_t, totmoney=500)
    cm_m.bcmkset(xa.indexinfo('1399971'), start='2016-09-28')
    assert round(cm_m.xirrrate('2018-07-29'), 3) == -0.129
    assert round(cm_m.sharpe('2018-07-30'), 3) == -1.734
    cm_m.v_netvalue(benchmark=False)
    assert round(cm_m.total_return('2018-07-01'), 3) == -0.209
    assert round(cm_m.benchmark_volatility('2018-07-22'), 3) == 0.192
    assert round(cm_m.max_drawdown('2018-08-01')[2], 2) == -0.24
    cm_m.v_tradevolume()


def test_mulfix():
    tot = xa.mulfix(status=statb, totmoney=5000)
    tot.v_positions()
    tot.v_positions_history('2017-01-01')
    assert round(tot.combsummary('2018-08-04').iloc[0]['投资收益率'], 1) == 1.0
    eva = tot.evaluation()
    assert round(eva.correlation_table(end='2018-07-30').iloc[2, 4], 3) == 0.095


def test_policy_buyandhold():
    allin = xa.policy.buyandhold(cm, '2015-06-01')
    cm_t2 = xa.trade(cm, allin.status)
    cm_m2 = xa.mulfix(cm_t2)
    cm_m2.bcmkset(xa.indexinfo('1399971'))
    assert round(cm_m2.correlation_coefficient('2018-07-01'), 3) == 0.980
    assert round(cm_m2.information_ratio('2016-07-01'), 3) == -0.385
    allin.sellout('2018-06-01')
    cm_t2 = xa.trade(cm, allin.status)
    assert round(cm_t2.xirrrate('2019-08-12', guess=-0.9), 2) == -0.33


def test_policy_scheduled():
    auto = xa.policy.scheduled(cm, 1000, pd.date_range('2015-07-01', '2018-07-01', freq='W-THU'))
    cm_t3 = xa.trade(cm, auto.status)
    cm_t3.v_tradevolume(freq='W')
    assert round(cm_t3.dailyreport('2018-08-03').iloc[0]['投资收益率'], 2) == -42.07
    auto2 = xa.policy.scheduled_tune(cm, 1000, pd.date_range('2015-07-01', '2018-07-01', freq='M'),
                                     [(0.9, 2), (1.2, 1)])


def test_policy_grid():
    gr = xa.policy.grid(cm, [0, 2, 2], [3, 3, 3], '2018-06-23', '2018-08-03')
    tr = xa.trade(cm, gr.status)
    assert round(tr.xirrrate('2018-07-13'), 2) == 11.78


def test_policy_indicator_cross():
    cm.bbi()
    techst = xa.policy.indicator_cross(cm, col=['netvalue', 'BBI'], start='2018-01-01', end='2018-07-07')
    cm_tt = xa.trade(cm, techst.status)
    assert round(cm_tt.dailyreport('2018-07-09').iloc[0].loc['换手率'], 1) == 14.1


def test_policy_indicator_points():
    zz500 = xa.indexinfo('0000905')
    zz500.psy()
    st = xa.policy.indicator_points(zz500, col='PSYMA12', start='2017-01-01', buy=[(0.6, 1), (0.7, 1)],
                                    sell=[(0.4, 1), (0.3, 1)], buylow=False)
    zz500_t = xa.trade(zz500, st.status)
    assert zz500_t.dailyreport('2018-05-01').iloc[0].loc['基金收益总额'] == -6302.26


def test_record_list():
    tot = xa.mulfix(status=statl, totmoney=50000, **ioconf)
    assert round(tot.combsummary('2019-05-04').iloc[0]['投资收益率'], 1) == 10.6
