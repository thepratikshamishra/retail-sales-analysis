"""Regression tests on the real Sample Superstore file.

Skipped automatically if data/raw/superstore.csv has not been downloaded.
The expected numbers were obtained by inspecting the file (and cross-checked
below with a plain pandas calculation that does not use this project's code),
so these tests pin the behaviour for THAT version of the file (see the
SHA-256 test).
"""
from pathlib import Path

import pandas as pd
import pytest

from src.analysis import compute_kpis, returns_stats
from src.clean import prepare_data
from src.load_data import EXPECTED_SHA256, read_sections, sha256_of_file

RAW = Path("data/raw/superstore.csv")
pytestmark = pytest.mark.skipif(not RAW.exists(), reason="real data not downloaded")


@pytest.fixture(scope="module")
def real():
    return prepare_data(read_sections(RAW))


def test_file_matches_pinned_checksum():
    assert sha256_of_file(RAW) == EXPECTED_SHA256


def test_sections_have_expected_sizes():
    sections = read_sections(RAW)
    assert len(sections["orders"]) == 9994
    assert len(sections["people"]) == 4
    assert len(sections["returns"]) == 800


def test_cleaning_keeps_every_order_line(real):
    assert len(real.orders) == 9994
    assert real.rejected.empty
    assert int(real.orders["possible_duplicate"].sum()) == 1   # Row IDs 3406/3407
    assert int(real.orders["Postal Code"].isna().sum()) == 11  # all Burlington, Vermont
    assert real.orders["Postal Code"].dropna().str.len().eq(5).all()


def test_headline_numbers(real):
    k = compute_kpis(real.orders)
    assert k["total_sales"] == pytest.approx(2297200.8603, abs=0.01)
    assert k["total_profit"] == pytest.approx(286397.0217, abs=0.01)
    assert k["total_quantity"] == 37873
    assert k["orders"] == 5009 and k["customers"] == 793
    assert (k["date_start"], k["date_end"]) == ("2015-01-03", "2018-12-30")


def test_pipeline_totals_agree_with_plain_pandas(real):
    plain = pd.read_csv(RAW, nrows=9994)  # Orders block only; no project code involved
    k = compute_kpis(real.orders)
    assert k["total_sales"] == pytest.approx(plain["Sales"].sum())
    assert k["total_profit"] == pytest.approx(plain["Profit"].sum())
    assert k["total_quantity"] == plain["Quantity"].sum()
    assert k["orders"] == plain["Order ID"].nunique()


def test_returned_orders(real):
    stats = returns_stats(real.orders)
    assert stats["returned_orders"] == 296
    assert stats["orders"] == 5009
