"""
一个简单展示 qdii 实时净值预测的例子，最大限度的利用缓存而减少网络请求
"""

import pandas as pd
import xalpha as xa
import logging

xa.set_backend(backend="csv", path="../../../lof/data", precached="20200103")
# xa.set_proxy("socks5://127.0.0.1:1080")

logger = logging.getLogger("xalpha")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


@xa.universal.lru_cache_time(ttl=60)
def cached_get_rt(code, **kws):
    return xa.get_rt(code, handler=False)


@xa.universal.lru_cache_time(ttl=1800)
def cached_get_bar(code, *args, **kws):
    if code.startswith("commodities/"):
        kws["handler"] = False
        return xa.get_bar(code, *args, **kws)
    return None


xa.set_handler(method="rt", f=cached_get_rt)
xa.set_handler(method="bar", f=cached_get_bar)


qdiis = [
    "SH501018",
    "SZ160416",
    "SZ161129",
    "SZ160723",
    "SZ160216",
    "SZ162411",
    "SZ163208",
    "SZ162719",
    "SZ165513",
    "SZ161815",
    "SZ161116",
    "SZ164701",
    "SZ160719",
    "SZ164824",
    "SH513030",
    "SZ161714",
]
data = {
    "code": [],
    "name": [],
    "t1": [],
    "t0": [],
    "now": [],
    "t1rate": [],
    "t0rate": [],
    "positions": [],
}
for c in qdiis:
    p = xa.QDIIPredict(c, fetch=True, save=True)
    try:
        data["t1"].append(round(p.get_t1(return_date=False), 4))
        data["t1rate"].append(round(p.get_t1_rate(return_date=False), 2))
        try:
            data["t0"].append(round(p.get_t0(return_date=False), 4))
            data["t0rate"].append(round(p.get_t0_rate(return_date=False), 2))
        except ValueError:
            data["t0"].append("-")
            data["t0rate"].append("-")
        data["positions"].append(round(p.get_position(return_date=False), 3))
        data["now"].append(xa.get_rt(c)["current"])
        data["code"].append(c)
        data["name"].append(xa.get_rt(c)["name"])
    except xa.exceptions.NonAccurate:
        print("%s cannot be predicted exactly now" % c)
df = pd.DataFrame(data)
with open("demo.html", "w") as f:
    df.to_html(f)
