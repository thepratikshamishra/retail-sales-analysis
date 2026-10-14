import numpy as np
import pandas as pd
import pytest

from src.clean import (
    CleaningError,
    CleaningReport,
    clean_orders,
    clean_people,
    clean_returns,
    flag_returned_orders,
    prepare_data,
)
from tests.helpers import order_row, raw_orders_frame, synthetic_order_rows


def clean_rows(rows, **kwargs):
    return clean_orders(raw_orders_frame(rows), **kwargs)


def reasons_for(rejected, row_id):
    return rejected.loc[rejected["Row ID"] == str(row_id), "reject_reason"].iloc[0]


# ---- types -----------------------------------------------------------------
def test_column_types_after_cleaning():
    df, rejected, _ = clean_rows(synthetic_order_rows())
    assert rejected.empty
    assert pd.api.types.is_datetime64_any_dtype(df["Order Date"])
    assert pd.api.types.is_datetime64_any_dtype(df["Ship Date"])
    assert df["Sales"].dtype == "float64"
    assert df["Quantity"].dtype == "int64"
    assert str(df["Row ID"].dtype) == "Int64"


def test_dates_are_parsed_month_first():
    df, _, _ = clean_rows(synthetic_order_rows())
    assert df.loc[0, "Order Date"] == pd.Timestamp(2020, 1, 5)  # "1/5/2020" = 5 January
    assert df.loc[0, "order_year"] == 2020 and df.loc[0, "order_month_num"] == 1


def test_postal_code_leading_zero_restored_and_missing_not_invented():
    df, _, _ = clean_rows(synthetic_order_rows())
    assert df.loc[0, "Postal Code"] == "01040"
    assert df.loc[1, "Postal Code"] == "90001"
    assert pd.isna(df.loc[2, "Postal Code"])  # stays missing, never imputed


def test_postal_code_with_decimal_suffix_is_repaired():
    row = order_row(1, "O1", "1/5/2020", "1/8/2020", postal="2134.0")
    df, _, _ = clean_rows([row])
    assert df.loc[0, "Postal Code"] == "02134"


def test_whitespace_is_trimmed_and_blank_becomes_missing():
    row = order_row(1, "O1", "1/5/2020", "1/8/2020", region="  West ", postal="   ")
    df, _, report = clean_rows([row])
    assert df.loc[0, "Region"] == "West"
    assert pd.isna(df.loc[0, "Postal Code"])


def test_case_variants_of_labels_are_harmonised_to_commonest_spelling():
    rows = [order_row(i, f"O{i}", "1/5/2020", "1/8/2020", region=r)
            for i, r in enumerate(["West", "West", "west", "WEST "], start=1)]
    df, _, _ = clean_rows(rows)
    assert set(df["Region"]) == {"West"}


def test_product_names_are_not_case_harmonised():
    rows = [order_row(1, "O1", "1/5/2020", "1/8/2020", product_name="iPhone"),
            order_row(2, "O2", "1/5/2020", "1/8/2020", product_name="IPHONE")]
    df, _, _ = clean_rows(rows)
    assert set(df["Product Name"]) == {"iPhone", "IPHONE"}


# ---- invalid records -------------------------------------------------------
@pytest.mark.parametrize("kwargs, expected", [
    ({"sales": -5}, "Sales <= 0"),
    ({"sales": 0}, "Sales <= 0"),
    ({"sales": "abc"}, "missing or unparseable Sales"),
    ({"quantity": 0}, "Quantity not a whole number"),
    ({"quantity": 2.5}, "Quantity not a whole number"),
    ({"discount": 1.5}, "Discount outside 0-1"),
    ({"discount": -0.1}, "Discount outside 0-1"),
    ({"profit": "inf"}, "Profit not finite"),
    ({"profit": None}, "missing or unparseable Profit"),
    ({"order_date": "13/45/2020"}, "missing or unparseable Order Date"),
    ({"order_date": "2020-01-05"}, "missing or unparseable Order Date"),
    ({"ship_date": "not a date"}, "unparseable Ship Date"),
    ({"ship_date": "1/1/2020"}, "Ship Date before Order Date"),
    ({"customer_id": None}, "missing or unparseable Customer ID"),
])
def test_invalid_rows_are_rejected_with_reason(kwargs, expected):
    base = dict(order_date="1/5/2020", ship_date="1/8/2020")
    base.update(kwargs)
    good = order_row(1, "O1", "1/5/2020", "1/8/2020")
    bad = order_row(2, "O2", **base)
    df, rejected, report = clean_rows([good, bad])
    assert list(df["Row ID"]) == [1]
    assert len(rejected) == 1
    assert expected in reasons_for(rejected, 2)


def test_one_row_can_have_several_reasons():
    bad = order_row(2, "O2", "1/5/2020", "1/8/2020", sales=-1, quantity=0)
    _, rejected, _ = clean_rows([order_row(1, "O1", "1/5/2020", "1/8/2020"), bad])
    reason = reasons_for(rejected, 2)
    assert "Sales <= 0" in reason and "Quantity" in reason


def test_missing_ship_date_alone_is_allowed():
    row = order_row(1, "O1", "1/5/2020", None)
    df, rejected, _ = clean_rows([row])
    assert len(df) == 1 and rejected.empty
    assert pd.isna(df.loc[0, "ship_days"])


def test_rejected_rows_keep_original_raw_text():
    bad = order_row(2, "O2", "1/5/2020", "1/8/2020", sales="abc")
    _, rejected, _ = clean_rows([order_row(1, "O1", "1/5/2020", "1/8/2020"), bad])
    assert rejected.loc[0, "Sales"] == "abc"


def test_all_rows_invalid_gives_empty_clean_frame_without_crashing():
    df, rejected, _ = clean_rows([order_row(1, "O1", "1/5/2020", "1/8/2020", sales=-1)])
    assert df.empty and len(rejected) == 1


# ---- duplicates ------------------------------------------------------------
def test_ambiguous_duplicate_is_kept_and_flagged_by_default():
    df, _, report = clean_rows(synthetic_order_rows())
    assert len(df) == 7
    assert list(df.loc[df["possible_duplicate"], "Row ID"]) == [7]  # later copy is flagged
    step = next(s for s in report.steps if s["step"].startswith("Ambiguous"))
    assert step["affected"] == 1 and "KEPT" in step["decision"]


def test_drop_policy_removes_later_copy():
    df, _, report = clean_rows(synthetic_order_rows(), duplicate_policy="drop")
    assert len(df) == 6
    assert 7 not in set(df["Row ID"]) and 6 in set(df["Row ID"])


def test_exact_duplicate_including_row_id_is_removed():
    rows = synthetic_order_rows()
    rows.append(list(rows[0]))  # identical in every column, Row ID too
    df, _, report = clean_rows(rows)
    assert len(df) == 7
    step = next(s for s in report.steps if s["step"].startswith("Exact duplicate"))
    assert step["affected"] == 1


def test_same_row_id_with_different_content_is_reported_not_deleted():
    rows = [order_row(1, "O1", "1/5/2020", "1/8/2020", sales=10),
            order_row(1, "O2", "1/5/2020", "1/8/2020", sales=20)]
    df, _, report = clean_rows(rows)
    assert len(df) == 2
    step = next(s for s in report.steps if s["step"].startswith("Row ID uniqueness"))
    assert step["affected"] == 1


def test_unknown_duplicate_policy_raises():
    with pytest.raises(CleaningError, match="duplicate_policy"):
        clean_rows(synthetic_order_rows(), duplicate_policy="maybe")


# ---- derived columns -------------------------------------------------------
def test_row_margin_is_profit_over_sales_and_finite():
    df, _, _ = clean_rows(synthetic_order_rows())
    assert df.loc[0, "row_margin"] == pytest.approx(0.2)
    assert df.loc[3, "row_margin"] == pytest.approx(-0.5)
    assert np.isfinite(df["row_margin"]).all()


def test_is_loss_and_ship_days():
    df, _, _ = clean_rows(synthetic_order_rows())
    assert list(df["is_loss"]) == [False, False, True, True, False, False, False]
    assert df.loc[0, "ship_days"] == 3


def test_input_frame_is_not_modified():
    raw = raw_orders_frame(synthetic_order_rows())
    before = raw.copy(deep=True)
    clean_orders(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_missing_required_column_raises():
    raw = raw_orders_frame(synthetic_order_rows()).drop(columns=["Sales"])
    with pytest.raises(CleaningError, match="Sales"):
        clean_orders(raw)


def test_report_markdown_lists_every_step():
    _, _, report = clean_rows(synthetic_order_rows())
    text = report.to_markdown()
    assert text.count("\n|") >= len(report.steps) + 2
    assert "Ambiguous duplicates" in text


# ---- returns and people ----------------------------------------------------
def test_returns_deduplicated_to_unique_orders(sections):
    report = CleaningReport()
    returns = clean_returns(sections["returns"], report)
    assert sorted(returns["Order ID"]) == ["O3", "O999"]


def test_returns_with_non_yes_and_blank_ids_are_ignored():
    raw = pd.DataFrame([["Yes", "O1"], ["No", "O2"], ["Yes", ""], ["yes", "O3"]],
                       columns=["Returned", "Order ID"])
    returns = clean_returns(raw, CleaningReport())
    assert sorted(returns["Order ID"]) == ["O1", "O3"]


def test_flag_returned_orders_flags_all_lines_and_counts_unmatched(cleaned):
    orders = cleaned.orders
    assert list(orders.loc[orders["is_returned"], "Order ID"]) == ["O3"]
    step = next(s for s in cleaned.report.steps if "not found in Orders" in s["step"])
    assert step["affected"] == 1  # O999 does not exist in Orders


def test_missing_returns_section_disables_returns_analysis(tmp_path):
    from src.load_data import read_sections
    from tests.helpers import build_csv_text
    path = tmp_path / "x.csv"
    path.write_text(build_csv_text(include_returns=False), encoding="utf-8")
    result = prepare_data(read_sections(path))
    assert result.returns_available is False
    assert not result.orders["is_returned"].any()


def test_people_duplicates_dropped_and_unknown_regions_reported(cleaned):
    raw = pd.DataFrame([["Anna", "West"], ["Zed", "West"], ["Ben", "East"], ["Max", "Mars"]],
                       columns=["Person", "Region"])
    people = clean_people(raw, cleaned.orders, CleaningReport())
    assert dict(zip(people["Region"], people["Person"])) == {
        "West": "Anna", "East": "Ben", "Mars": "Max"}
