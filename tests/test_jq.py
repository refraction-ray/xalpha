import sys

sys.path.insert(0, "../")
import xalpha as xa

xa.provider.set_jq_data(debug=True)


def test_jq_provider():
    assert xa.show_providers() == ["jq"]


def test_peb_history():
    xa.set_backend(backend="csv", path="./")
    h = xa.universal.PEBHistory("SH000807", end="20200302")
    h.summary()
    h.v()  # matplotlib is required for this
    assert round(h.df.iloc[0]["pe"], 2) == 19.67


def test_iw():
    xa.set_backend(backend="csv", path="./")
    df = xa.get_daily("iw-399006.XSHE", end="20200226")
    assert (
        df[(df["date"] == "2019-04-01") & (df["code"] == "300271.XSHE")].iloc[0].weight
        == 0.9835
    )
    df = xa.universal.get_index_weight_range(
        "399006.XSHE", start="2018-01-01", end="2020-02-01"
    )
    assert (
        df[(df["date"] == "2019-04-01") & (df["code"] == "300271.XSHE")].iloc[0].weight
        == 0.9835
    )


def test_peb_range():
    xa.set_backend(backend="csv", path="./")
    df = xa.get_daily("peb-000807.XSHG", prev=100, end="20200202")
    assert round(df[df["date"] == "2020-01-03"].iloc[0]["pe"], 2) == 30.09
