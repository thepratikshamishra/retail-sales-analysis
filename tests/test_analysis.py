"""Metric tests. Expected numbers are worked out by hand in tests/helpers.py."""
import math

import numpy as np
import pandas as pd
import pytest

from src import analysis as an
from src.clean import prepare_data
from src.load_data import ORDERS_COLUMNS, read_sections
from tests.helpers import build_csv_text, order_row


# ---- safe_divide -----------------------------------------------------------
def test_safe_divide_scalars():
    assert an.safe_divide(10, 4) == 2.5
    assert math.isnan(an.safe_divide(5, 0))
    assert math.isnan(an.safe_divide(0, 0))
    assert math.isnan(an.safe_divide(float("nan"), 3))


def test_safe_divide_series_has_nan_instead_of_inf():
    out = an.safe_divide(pd.Series([1.0, 2.0, 3.0]), pd.Series([2.0, 0.0, 4.0]))
    assert out.iloc[0] == 0.5 and out.iloc[2] == 0.75
    assert math.isnan(out.iloc[1])
    assert not np.isinf(out).any()


def test_safe_divide_series_by_scalar_keeps_index():
    out = an.safe_divide(pd.Series([2.0, 4.0], index=["a", "b"]), 2)
    assert list(out.index) == ["a", "b"] and list(out) == [1.0, 2.0]


# ---- headline numbers ------------------------------------------------------
def test_kpis_match_hand_calculation(cleaned):
    k = an.compute_kpis(cleaned.orders)
    assert k["total_sales"] == pytest.approx(760)
    assert k["total_profit"] == pytest.approx(111)
    assert k["total_quantity"] == 14
    assert k["orders"] == 5 and k["customers"] == 3 and k["order_lines"] == 7
    assert k["products"] == 3  # (P1, Chair), (P2, Phone), (P3, Paper)
    assert k["aggregate_profit_margin"] == pytest.approx(111 / 760)
    assert k["avg_order_value"] == pytest.approx(760 / 5)
    assert k["loss_making_lines"] == 2
    assert k["possible_duplicate_lines"] == 1
    assert (k["date_start"], k["date_end"]) == ("2020-01-05", "2020-03-05")


def test_aggregate_margin_and_mean_row_margin_are_different_measures(cleaned):
    k = an.compute_kpis(cleaned.orders)
    assert k["mean_row_margin"] == pytest.approx(0.45 / 7)
    assert k["aggregate_profit_margin"] != pytest.approx(k["mean_row_margin"])


def test_category_summary_values(cleaned):
    table = an.category_summary(cleaned.orders).set_index("Category")
    assert table.loc["Technology", "sales"] == pytest.approx(360)
    assert table.loc["Technology", "profit"] == pytest.approx(66)
    assert table.loc["Technology", "profit_margin"] == pytest.approx(66 / 360)
    assert table.loc["Furniture", "profit_margin"] == pytest.approx(0.05)
    assert table.loc["Office Supplies", "quantity"] == 8
    assert table["sales"].sum() == pytest.approx(760)
    assert table["sales_share"].sum() == pytest.approx(1.0)
    assert list(table.index) == ["Technology", "Office Supplies", "Furniture"]  # by profit


def test_region_summary_includes_person_from_people_table(cleaned):
    table = an.region_summary(cleaned.orders, cleaned.people).set_index("Region")
    assert table.loc["West", "person_listed_for_region"] == "Anna"
    assert table.loc["West", "profit"] == pytest.approx(70)
    assert table.loc["East", "profit"] == pytest.approx(-35)
    assert pd.isna(table.loc["South", "person_listed_for_region"])  # not in People table


def test_state_and_segment_summaries(cleaned):
    state = an.state_summary(cleaned.orders).set_index("State")
    assert state.loc["Texas", "sales"] == pytest.approx(310)
    segment = an.segment_summary(cleaned.orders).set_index("Segment")
    assert segment.loc["Corporate", "orders"] == 2


def test_summarize_group_with_zero_sales_gives_nan_margin_not_error():
    df = pd.DataFrame({
        "Order ID": ["A", "B"], "Customer ID": ["c", "c"], "Quantity": [1, 1],
        "Sales": [0.0, 10.0], "Profit": [0.0, 2.0], "Discount": [0.0, 0.0],
        "is_loss": [False, False], "g": ["zero", "ten"]})
    table = an.summarize(df, "g").set_index("g")
    assert math.isnan(table.loc["zero", "profit_margin"])
    assert table.loc["ten", "profit_margin"] == pytest.approx(0.2)


def test_customer_summary(cleaned):
    cust = an.customer_summary(cleaned.orders).set_index("Customer ID")
    assert cust.loc["C3", "sales"] == pytest.approx(310)
    assert cust.loc["C3", "orders"] == 2
    assert cust.loc["C2", "customer_name"] == "Bob"
    assert cust.loc["C2", "profit"] == pytest.approx(-35)
    assert cust.index[0] == "C1" or cust["sales"].iloc[0] == cust["sales"].max()


def test_customer_concentration_numbers():
    customers = pd.DataFrame({"sales": [50.0, 30.0, 10.0, 10.0], "profit": [5, -1, 2, 3],
                              "orders": [3, 1, 2, 1]})
    stats, curve = an.customer_concentration(customers)
    assert stats["customers"] == 4
    assert stats["top_10_customers_sales_share"] == pytest.approx(1.0)
    assert stats["top_20pct_customers_n"] == 1
    assert stats["top_20pct_customers_sales_share"] == pytest.approx(0.5)
    assert stats["loss_making_customers"] == 1
    assert stats["customers_with_2plus_orders_share"] == pytest.approx(0.5)
    assert list(curve["cumulative_sales_share"]) == pytest.approx([0.5, 0.8, 0.9, 1.0])
    assert list(curve["customer_share"]) == pytest.approx([0.25, 0.5, 0.75, 1.0])


def test_product_stats_counts_loss_makers(cleaned):
    products = an.product_summary(cleaned.orders)
    stats = an.product_stats(products)
    assert stats["products"] == 3
    assert stats["loss_making_products"] == 0  # Chair +10, Phone +66, Paper +35
    assert stats["profit_of_profitable_products"] == pytest.approx(111)


# ---- time ------------------------------------------------------------------
def test_incomplete_year_gets_no_growth_figure(cleaned):
    yearly = an.yearly_summary(cleaned.orders)
    assert yearly.loc[0, "months_with_orders"] == 3
    assert math.isnan(yearly.loc[0, "sales_growth"])


def _two_full_years():
    rows, row_id = [], 1
    for year, sales in [(2019, 100.0), (2020, 150.0)]:
        for month in range(1, 13):
            rows.append(order_row(row_id, f"O{row_id}", f"{month}/10/{year}", f"{month}/12/{year}",
                                  sales=sales, profit=sales * 0.1))
            row_id += 1
    return rows


def test_growth_between_complete_years(tmp_path):
    path = tmp_path / "two_years.csv"
    path.write_text(build_csv_text(order_rows=_two_full_years(), include_people=False,
                                   include_returns=False), encoding="utf-8")
    data = prepare_data(read_sections(path))
    yearly = an.yearly_summary(data.orders)
    assert list(yearly["order_year"]) == [2019, 2020]
    assert yearly.loc[1, "sales_growth"] == pytest.approx(0.5)
    assert yearly.loc[1, "profit_growth"] == pytest.approx(0.5)
    assert math.isnan(yearly.loc[0, "sales_growth"])
    season = an.seasonality(data.orders)
    assert len(season) == 12 and season["years_observed"].eq(2).all()
    assert season["avg_monthly_sales"].iloc[0] == pytest.approx(125)


def test_monthly_summary_and_year_month_grid(cleaned):
    monthly = an.monthly_summary(cleaned.orders)
    assert list(monthly["month_num"]) == [1, 2, 3]
    assert list(monthly["sales"]) == pytest.approx([300, 150, 310])
    grid = an.sales_by_year_month(cleaned.orders)
    assert grid.loc[2020, 3] == pytest.approx(310)
    assert pd.isna(grid.loc[2020].get(4, np.nan))  # no April orders -> missing, not zero


# ---- discounts -------------------------------------------------------------
@pytest.mark.parametrize("value, label", [
    (0.0, "0%"), (0.05, ">0-10%"), (0.10, ">0-10%"), (0.15, ">10-20%"), (0.20, ">10-20%"),
    (0.21, ">20-30%"), (0.30, ">20-30%"), (0.32, ">30-50%"), (0.50, ">30-50%"),
    (0.51, ">50%"), (0.80, ">50%")])
def test_discount_band_edges(value, label):
    assert str(an.discount_band(pd.Series([value])).iloc[0]) == label


def test_discount_band_summary_values(cleaned):
    bands = an.discount_band_summary(cleaned.orders).set_index("discount_band")
    assert bands.loc["0%", "sales"] == pytest.approx(450)
    assert bands.loc[">0-10%", "order_lines"] == 2
    assert bands.loc[">0-10%", "profit_margin"] == pytest.approx(0.1)
    assert bands.loc[">30-50%", "loss_line_share"] == pytest.approx(1.0)
    assert bands["order_lines"].sum() == 7


def test_spearman_is_minus_one_for_perfectly_opposed_ranks():
    df = pd.DataFrame({"Discount": [0.0, 0.1, 0.2, 0.3], "row_margin": [0.4, 0.2, 0.0, -0.3]})
    bands = pd.DataFrame({"discount_band": ["a", "b"], "profit_margin": [0.1, -0.1]})
    stats = an.discount_stats(df, bands)
    assert stats["spearman_discount_vs_row_margin"] == pytest.approx(-1.0)
    assert stats["first_band_with_negative_margin"] == "b"


def test_no_negative_band_gives_none():
    df = pd.DataFrame({"Discount": [0.0, 0.1], "row_margin": [0.2, 0.1]})
    bands = pd.DataFrame({"discount_band": ["a"], "profit_margin": [0.1]})
    assert an.discount_stats(df, bands)["first_band_with_negative_margin"] is None


# ---- returns ---------------------------------------------------------------
def test_return_rate_by_region(cleaned):
    table = an.return_rate_by(cleaned.orders, "Region").set_index("Region")
    assert table.loc["East", "return_rate"] == pytest.approx(0.5)  # O3 of {O2, O3}
    assert table.loc["West", "return_rate"] == 0
    assert table.loc["South", "return_rate"] == 0
    assert table.loc["East", "share_of_sales_in_returned_orders"] == pytest.approx(50 / 150)
    assert table.index[0] == "East"  # sorted by rate


def test_returns_stats_and_comparison(cleaned):
    stats = an.returns_stats(cleaned.orders)
    assert stats["orders"] == 5 and stats["returned_orders"] == 1
    assert stats["overall_return_rate"] == pytest.approx(0.2)
    assert stats["share_of_sales_in_returned_orders"] == pytest.approx(50 / 760)
    cmp_ = an.returns_comparison(cleaned.orders).set_index("group")
    assert cmp_.loc["Returned", "orders"] == 1
    assert cmp_.loc["Returned", "avg_order_value"] == pytest.approx(50)
    assert cmp_.loc["Not returned", "orders"] == 4
    assert cmp_.loc["Not returned", "sales"] == pytest.approx(710)
    assert cmp_.loc["Returned", "profit_margin"] == pytest.approx(-0.5)


# ---- helpers and the combined run ------------------------------------------
def test_top_and_bottom_has_no_repeats_when_table_is_short():
    table = pd.DataFrame({"x": range(15)})
    assert len(an.top_and_bottom(table, "x", 10)) == 15
    assert len(an.top_and_bottom(pd.DataFrame({"x": range(25)}), "x", 10)) == 20
    ordered = an.top_and_bottom(pd.DataFrame({"x": range(25)}), "x", 3)
    assert list(ordered["x"]) == [24, 23, 22, 2, 1, 0]


def test_margin_matrix_has_nan_for_empty_combinations(cleaned):
    matrix = an.margin_matrix(cleaned.orders, "Sub-Category", "Region")
    assert matrix.loc["Phones", "West"] == pytest.approx(50 / 200)
    assert pd.isna(matrix.loc["Chairs", "South"])  # no such sales, so NaN not 0


def test_run_all_analyses_contains_expected_keys(cleaned):
    results = an.run_all_analyses(cleaned.orders, cleaned.people, cleaned.returns_available)
    for key in ["kpis", "yearly", "monthly", "category", "subcategory", "region", "state",
                "segment", "customers", "discount_bands", "returns_compare", "returns_stats",
                "margin_subcategory_region", "products", "lorenz"]:
        assert key in results


def test_run_all_analyses_without_returns_skips_return_tables(cleaned):
    results = an.run_all_analyses(cleaned.orders, cleaned.people, returns_available=False)
    assert "returns_stats" not in results and "returns_compare" not in results
    assert results["returns_available"] is False
