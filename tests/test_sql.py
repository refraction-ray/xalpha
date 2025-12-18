# -*- coding: utf-8 -*-
import pytest
import pandas as pd
from sqlalchemy import create_engine
import xalpha as xa
import os


def test_sql_io():
    # Use sqlite in-memory for testing
    engine = create_engine("sqlite:///:memory:")

    # Test fundinfo with sql backend
    code = "000311"

    try:
        # Create a fundinfo object
        fi = xa.fundinfo(code, fetch=False, save=True, path=engine, form="sql")

        # Verify it saved to SQL
        df_check = pd.read_sql("xa" + code, engine)
        assert len(df_check) > 0

        # Test fetch from SQL
        fi_fetch = xa.fundinfo(code, fetch=True, save=False, path=engine, form="sql")
        assert len(fi_fetch.price) == len(fi.price)
        assert fi_fetch.name == fi.name

    finally:
        engine.dispose()


def test_mfund_sql_io():
    engine = create_engine("sqlite:///:memory:")
    code = "001211"
    try:
        mfi = xa.mfundinfo(code, fetch=False, save=True, path=engine, form="sql")
        df_check = pd.read_sql("xa" + code, engine)
        assert len(df_check) > 0

        mfi_fetch = xa.mfundinfo(code, fetch=True, save=False, path=engine, form="sql")
        assert len(mfi_fetch.price) == len(mfi.price)
    finally:
        engine.dispose()
