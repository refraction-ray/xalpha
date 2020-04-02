__version__ = "0.8.2"
__author__ = "refraction-ray"
__name__ = "xalpha"

import xalpha.policy
import xalpha.remain
from xalpha.evaluate import evaluate
from xalpha.info import fundinfo, indexinfo, cashinfo, mfundinfo, FundReport
from xalpha.multiple import mul, mulfix, imul
from xalpha.realtime import rfundinfo, review
from xalpha.record import record, irecord
from xalpha.trade import trade, itrade
from xalpha.universal import get_daily, get_rt, get_bar, set_backend
from xalpha.provider import show_providers, set_proxy
from xalpha.toolbox import PEBHistory, Compare, SWPEBHistory, QDIIPredict, set_holdings
