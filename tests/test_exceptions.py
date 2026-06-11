import pytest
from xalpha.exceptions import (
    XalphaException,
    FundTypeError,
    FundNotExistError,
    TradeBehaviorError,
    HttpStatusError,
    ParserFailure,
    DataSourceNotFound,
    DataPossiblyWrong,
    DateMismatch,
    NonAccurate,
)


def test_inheritance():
    assert issubclass(XalphaException, Exception)
    for exc in [
        FundTypeError,
        FundNotExistError,
        TradeBehaviorError,
        HttpStatusError,
        ParserFailure,
        DataSourceNotFound,
        DataPossiblyWrong,
        DateMismatch,
        NonAccurate,
    ]:
        assert issubclass(exc, XalphaException)


def test_basic_exceptions():
    for exc_class in [
        XalphaException,
        FundTypeError,
        FundNotExistError,
        TradeBehaviorError,
        HttpStatusError,
        ParserFailure,
        DataSourceNotFound,
        DataPossiblyWrong,
    ]:
        with pytest.raises(exc_class) as excinfo:
            raise exc_class("test message")
        assert str(excinfo.value) == "test message"


def test_date_mismatch():
    exc = DateMismatch("123", "mismatch")
    assert exc.code == "123"
    assert exc.reason == "mismatch"
    assert str(exc) == "mismatch"
    assert repr(exc) == "mismatch"


def test_non_accurate():
    exc = NonAccurate("456", "not accurate")
    assert exc.code == "456"
    assert exc.reason == "not accurate"
    assert str(exc) == "not accurate"
    assert repr(exc) == "not accurate"
