# -*- coding: utf-8 -*-
"""
exceptions in xalpha packages
"""


class XalphaException(Exception):
    pass


class FundTypeError(XalphaException):
    """
    The code mismatches the fund type obj, fundinfo/mfundinfo
    """

    pass


class FundNotExistError(XalphaException):
    """
    There is no fund with given code
    """

    pass


class TradeBehaviorError(XalphaException):
    """
    Used for unreal trade attempt, such as selling before buying
    """

    pass


class ParserFailure(XalphaException):
    """
    Used for exception when parsing fund APIs
    """

    pass
