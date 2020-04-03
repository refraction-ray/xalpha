import sys
import pytest

sys.path.insert(0, "../")
import xalpha as xa

xa.set_backend(backend="memory", prefix="pytest-")


def test_compare():
    c = xa.Compare(("37450", "USD"), "SH501018", start="20200101")
    c.corr()
    c.v()


def test_get_currency():
    assert (
        xa.toolbox.get_currency_code("indices/india-50-futures") == "currencies/inr-cny"
    )
    assert xa.toolbox._get_currency_code("JPY") == "100JPY/CNY"


def test_qdii_predict():
    hb = xa.QDIIPredict(
        "SZ162411",
        t1dict={".SPSIOP": 91},
        t0dict={"commodities/brent-oil": 40 * 0.9, "commodities/crude-oil": 60 * 0.9,},
        positions=True,
    )
    hb.get_t1()
    hb.get_t0(percent=True)
    hb.benchmark_test("20200202", "20200302")
    hb.analyse()


@pytest.mark.local
def test_qdii_predict_local():
    xc = xa.QDIIPredict("SZ165513", positions=True)
    xc.get_t0_rate()
