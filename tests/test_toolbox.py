import sys

sys.path.insert(0, "../")
import xalpha as xa

xa.set_backend(backend="memory", prefix="pytest-")


def test_compare():
    c = xa.Compare(("37450", "USD"), "SH501018", start="20200101")
    c.corr()
    c.v()


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
