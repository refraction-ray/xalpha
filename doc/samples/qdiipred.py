"""
一个简单展示 qdii 实时净值预测的例子，最大限度的利用缓存而减少网络请求
"""

import pandas as pd
import xalpha as xa

xa.set_backend(backend="csv", path="../../../lof/data", precached="20200103")


@xa.universal.lru_cache_time(ttl=60)
def cached_get_rt(code, **kws):
    return xa.get_rt(code, handler=False)


@xa.universal.lru_cache_time(ttl=1800)
def cached_get_bar(code, *args, **kws):
    if code.startswith("commodities/"):
        return xa.get_bar(code, handler=False, *args, **kws)
    return None


xa.set_handler(method="rt", f=cached_get_rt)
xa.set_handler(method="bar", f=cached_get_bar)


qdiis = ["SH501018", "SZ160416", "SZ161129", "SZ160723", "SZ160216"]
data = {"code": [], "t1": [], "t0": [], "t1rate": [], "t0rate": []}
for c in qdiis:
    p = xa.QDIIPredict(c, fetch=True, save=True)
    try:
        data["t1"].append(p.get_t1(return_date=False))
        data["t1rate"].append(p.get_t1_rate(return_date=False))
        data["t0"].append(p.get_t0(return_date=False))
        data["t0rate"].append(p.get_t0_rate(return_date=False))
        data["code"].append(c)
    except xa.exceptions.NonAccurate:
        print("%s cannot be predicted exactly now" % c)
df = pd.DataFrame(data)
with open("demo.html", "w") as f:
    df.to_html(f)
