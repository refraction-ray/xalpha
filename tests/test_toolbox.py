import sys

sys.path.insert(0, "../")
import xalpha as xa

xa.set_backend(backend="memory", prefix="pytest-")


def test_compare():
    c = xa.Compare(("37450", "USD"), "SH501018", start="20200101")
    c.corr()
    c.v()
