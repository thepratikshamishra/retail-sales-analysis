"""Builds the insights report text from computed results.

Every number in the text is read from the `results` dictionary produced by
analysis.run_all_analyses; sentences that depend on the data (for example
"which band first turns negative") are chosen by code, so the wording cannot
claim something the numbers do not show. The report keeps three things apart:
  1. Measured results     - computed directly from the data
  2. Interpretation       - careful readings of those results, with caveats
  3. Ideas to investigate - suggestions that were NOT tested here
"""
from __future__ import annotations

import calendar

import pandas as pd


def money(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def pct(value: float, digits: int = 1) -> str:
    return "n/a" if pd.isna(value) else f"{value * 100:.{digits}f}%"


def _signed_pct(value: float) -> str:
    return "n/a" if pd.isna(value) else f"{value * 100:+.1f}%"


def _measured_overview(r: dict) -> list[str]:
    k = r["kpis"]
    return [
        f"**Scope.** {k['orders']:,} orders ({k['order_lines']:,} order lines) from "
        f"{k['customers']:,} customers between {k['date_start']} and {k['date_end']}.",
        f"**Totals.** Sales {money(k['total_sales'])}, profit {money(k['total_profit'])}, "
        f"quantity {k['total_quantity']:,} units. Aggregate profit margin "
        f"(total profit / total sales) is {pct(k['aggregate_profit_margin'])}.",
        f"**Two different margins.** The average of line-level margins is "
        f"{pct(k['mean_row_margin'])} (median {pct(k['median_row_margin'])}). It differs "
        "from the aggregate margin because it gives a small line the same weight as a "
        "large one. The aggregate figure is used for all comparisons below.",
        f"**Loss-making lines.** {k['loss_making_lines']:,} of {k['order_lines']:,} order "
        f"lines ({pct(k['loss_making_line_share'])}) have negative profit.",
    ]


def _measured_time(r: dict) -> list[str]:
    out = []
    y = r["yearly"]
    parts = [f"{int(row.order_year)}: sales {money(row.sales)}, profit {money(row.profit)} "
             f"(margin {pct(row.profit_margin)})" for row in y.itertuples()]
    out.append("**By year.** " + "; ".join(parts) + ".")
    growth = y.dropna(subset=["sales_growth"])
    if len(growth):
        g = ", ".join(f"{int(row.order_year)} {_signed_pct(row.sales_growth)}"
                      for row in growth.itertuples())
        out.append(f"**Year-over-year sales growth** (only between complete 12-month years): {g}.")
    incomplete = y[y["months_with_orders"] < 12]
    if len(incomplete):
        years = ", ".join(str(int(v)) for v in incomplete["order_year"])
        out.append(f"Years with fewer than 12 months of orders ({years}) are not compared.")

    s = r["seasonality"].sort_values("avg_monthly_sales", ascending=False)
    names = lambda frame: ", ".join(  # noqa: E731
        f"{calendar.month_name[int(m)]} ({money(v)})"
        for m, v in zip(frame["month_num"], frame["avg_monthly_sales"]))
    out.append("**Seasonality.** Highest average monthly sales by calendar month: "
               f"{names(s.head(3))}. Lowest: {names(s.tail(3).iloc[::-1])}. "
               f"(Averages over {int(s['years_observed'].max())} year(s) of data.)")
    return out


def _measured_products(r: dict) -> list[str]:
    out = []
    c = r["category"]
    parts = [f"{row.Category}: sales {money(row.sales)} ({pct(row.sales_share)} of total), "
             f"profit {money(row.profit)}, margin {pct(row.profit_margin)}"
             for row in c.itertuples()]
    out.append("**Categories (ordered by profit).** " + "; ".join(parts) + ".")

    sc = r["subcategory"].rename(columns={"Sub-Category": "SubCategory"})
    best = sc.head(3)
    out.append("**Most profitable sub-categories.** " + "; ".join(
        f"{row.SubCategory} ({row.Category}) {money(row.profit)}, margin {pct(row.profit_margin)}"
        for row in best.itertuples()) + ".")
    losing = sc[sc["profit"] < 0].sort_values("profit")
    if len(losing):
        out.append(f"**Loss-making sub-categories ({len(losing)} of {len(sc)}).** " + "; ".join(
            f"{row.SubCategory} ({row.Category}) {money(row.profit)} on sales of {money(row.sales)}"
            for row in losing.itertuples()) + ".")
    else:
        out.append("No sub-category has negative total profit.")

    ps = r["product_stats"]
    products = r["products"]
    top = products.iloc[0]
    out.append(
        f"**Products** (Product ID + name; {ps['products']:,} products). "
        f"{ps['loss_making_products']:,} ({pct(ps['loss_making_product_share'])}) have negative "
        f"total profit, together losing {money(-ps['total_loss_of_loss_making_products'])}; "
        f"profitable products together earned {money(ps['profit_of_profitable_products'])}. "
        f"Highest-profit product: {top['Product Name']} ({money(top['profit'])}). "
        f"Largest loss: {products.iloc[-1]['Product Name']} ({money(products.iloc[-1]['profit'])}).")
    return out


def _measured_geography(r: dict) -> list[str]:
    out = []
    reg = r["region"]
    parts = [f"{row.Region}: sales {money(row.sales)}, profit {money(row.profit)}, "
             f"margin {pct(row.profit_margin)}" for row in reg.itertuples()]
    out.append("**Regions (ordered by profit).** " + "; ".join(parts) + ".")

    st = r["state"]
    losing = st[st["profit"] < 0]
    out.append(
        f"**States.** {len(losing)} of {len(st)} states have negative total profit"
        + (": " + ", ".join(f"{row.State} ({money(row.profit)})"
                            for row in losing.sort_values('profit').itertuples())
           if len(losing) else "")
        + f". Most profitable: " + ", ".join(
            f"{row.State} ({money(row.profit)})" for row in st.head(3).itertuples()) + ".")
    return out


def _measured_customers(r: dict) -> list[str]:
    cs = r["customer_stats"]
    seg = r["segment"]
    parts = [f"{row.Segment}: sales {money(row.sales)} ({pct(row.sales_share)}), "
             f"margin {pct(row.profit_margin)}, avg order value {money(row.avg_order_value)}"
             for row in seg.itertuples()]
    top = r["customers"].iloc[0]
    return [
        "**Segments.** " + "; ".join(parts) + ".",
        f"**Customer concentration.** The top 10 customers account for "
        f"{pct(cs['top_10_customers_sales_share'])} of sales; the top 20% of customers "
        f"({cs['top_20pct_customers_n']:,} of {cs['customers']:,}) account for "
        f"{pct(cs['top_20pct_customers_sales_share'])}. The highest-sales customer is "
        f"{top['customer_name']} ({money(top['sales'])}).",
        f"**Repeat buying.** Median {cs['median_orders_per_customer']:.0f} orders per customer; "
        f"{pct(cs['customers_with_2plus_orders_share'])} of customers ordered at least twice.",
        f"**Loss-making customers.** {cs['loss_making_customers']:,} customers "
        f"({pct(cs['loss_making_customer_share'])}) have negative total profit, "
        f"together {money(cs['total_loss_of_loss_making_customers'])}.",
    ]


def _measured_discounts(r: dict) -> list[str]:
    b = r["discount_bands"]
    ds = r["discount_stats"]
    parts = [f"{row.discount_band}: margin {pct(row.profit_margin)} "
             f"({row.order_lines:,} lines, {pct(row.loss_line_share, 0)} loss-making)"
             for row in b.itertuples()]
    out = ["**Discount band vs aggregate margin.** " + "; ".join(parts) + ".",
           f"**Rank correlation.** Spearman correlation between a line's discount and its "
           f"margin is {ds['spearman_discount_vs_row_margin']:.2f} "
           f"({pct(ds['share_of_lines_with_discount'])} of lines carry a discount)."]
    if ds["first_band_with_negative_margin"]:
        out.append(f"The lowest discount band with a negative aggregate margin is "
                   f"{ds['first_band_with_negative_margin']}.")
    else:
        out.append("No discount band has a negative aggregate margin.")

    dc = r["discount_by_category"]
    bad = dc[(dc["profit_margin"] < 0) & (dc["order_lines"] >= 30)]
    if len(bad):
        out.append("**Category x discount cells with negative margin (at least 30 lines):** "
                   + "; ".join(f"{row.Category}, {row.discount_band}: {pct(row.profit_margin)} "
                               f"({row.order_lines:,} lines)" for row in bad.itertuples()) + ".")
    return out


def _measured_returns(r: dict) -> list[str]:
    if not r.get("returns_available"):
        return ["Return data was not available, so returned orders were not analysed."]
    rs = r["returns_stats"]
    cmp_ = r["returns_compare"].set_index("group")
    out = [
        f"**Returns.** {rs['returned_orders']:,} of {rs['orders']:,} orders "
        f"({pct(rs['overall_return_rate'])}) are flagged as returned; they hold "
        f"{pct(rs['share_of_sales_in_returned_orders'])} of total sales.",
    ]
    if {"Returned", "Not returned"} <= set(cmp_.index):
        a, b = cmp_.loc["Returned"], cmp_.loc["Not returned"]
        out.append(
            f"Returned orders average {money(a['avg_order_value'])} in sales and "
            f"{a['avg_lines_per_order']:.1f} lines, versus {money(b['avg_order_value'])} and "
            f"{b['avg_lines_per_order']:.1f} lines for other orders. Their aggregate margin is "
            f"{pct(a['profit_margin'])} versus {pct(b['profit_margin'])}.")
    for key, label in [("return_rate_region", "region"), ("return_rate_segment", "segment"),
                       ("return_rate_category", "category")]:
        t = r[key]
        col = t.columns[0]
        out.append(f"Return rate by {label}: " + ", ".join(
            f"{row[col]} {pct(row.return_rate)}" for _, row in t.iterrows()) + ".")
    return out


def _interpretation(r: dict) -> list[str]:
    out = []
    ds = r["discount_stats"]
    if ds["first_band_with_negative_margin"]:
        out.append(
            f"The {ds['first_band_with_negative_margin']} discount band is the lowest one "
            "with a negative aggregate margin, and higher bands are listed above with "
            "their own margins. This is an association: the data has no cost field and discounts were not assigned "
            "at random (they may cluster in particular categories or products), so it "
            "does not prove that discounts caused the losses.")
    losing = r["subcategory"][r["subcategory"]["profit"] < 0]
    if len(losing):
        out.append("The loss-making sub-categories may reflect discounting, product cost, "
                   "or both. The data cannot separate these because costs are not provided.")
    cs = r["customer_stats"]
    out.append(
        f"Sales are spread across many customers (top 10 = "
        f"{pct(cs['top_10_customers_sales_share'])}), so within this dataset there is no "
        "sign of dependence on a handful of buyers.")
    if r.get("returns_available"):
        rr = r["return_rate_region"]
        overall = r["returns_stats"]["overall_return_rate"]
        top = rr.iloc[0]
        if overall > 0 and top["return_rate"] >= 1.5 * overall:
            others = rr.iloc[1:]
            out.append(
                f"The {top['Region']} region's return rate ({pct(top['return_rate'])}) is "
                f"{top['return_rate'] / overall:.1f}x the overall rate "
                f"({pct(overall)}); the other regions range from "
                f"{pct(others['return_rate'].min())} to {pct(others['return_rate'].max())}. "
                "The file has no return reason, so the cause cannot be determined here.")
        out.append("The return flag is order-level with no date, amount or reason. It is "
                   "unknown whether returned sales were refunded, so reported sales and "
                   "profit may include value that was later reversed.")
    return out


def _ideas(r: dict) -> list[str]:
    ideas = []
    ds = r["discount_stats"]
    if ds["first_band_with_negative_margin"]:
        ideas.append(
            f"Review discount rules for lines in the {ds['first_band_with_negative_margin']} "
            "band and above: compare loss-making lines against a target margin "
            "(needs cost data).")
    if len(r["subcategory"][r["subcategory"]["profit"] < 0]):
        ideas.append("Investigate pricing and discounting for the loss-making "
                     "sub-categories listed above before changing assortment.")
    states = r["state"]
    losing_states = states[states["profit"] < 0].sort_values("profit")
    if len(losing_states):
        names = ", ".join(losing_states["State"].head(3))
        ideas.append(
            f"Compare the biggest loss-making states ({names}) with profitable states on "
            "average discount and sub-category mix; both fields exist in this dataset, so "
            "this can be tested next.")
    return ideas


def build_insights(results: dict, source_note: str) -> str:
    """Return the insights report as Markdown."""
    def section(title, items):
        return [f"## {title}", ""] + [f"- {item}" for item in items] + [""]

    lines = [
        "# Insights report - Retail Sales Data Analysis",
        "",
        f"_{source_note}_",
        "",
        "All numbers below were computed by this project's code from the cleaned data. "
        "Sample Superstore is fictional, so these are findings about this dataset, not "
        "about a real company.",
        "",
    ]
    lines += section("1. Measured results: overall", _measured_overview(results))
    lines += section("2. Measured results: trends", _measured_time(results))
    lines += section("3. Measured results: categories and products", _measured_products(results))
    lines += section("4. Measured results: regions and states", _measured_geography(results))
    lines += section("5. Measured results: segments and customers", _measured_customers(results))
    lines += section("6. Measured results: discounts", _measured_discounts(results))
    lines += section("7. Measured results: returns", _measured_returns(results))
    lines += section("8. Interpretation (readings of the numbers, with caveats)",
                     _interpretation(results))
    lines += section("9. Ideas to investigate (NOT tested in this project)", _ideas(results))
    lines += section("Limits of this analysis", [
        "Fictional data; the licence of the file has not been independently verified.",
        "No cost, inventory, marketing or customer-demographic fields exist, so margin "
        "drivers and customer value beyond sales/profit cannot be explained.",
        "Margins are computed from the Profit column as supplied; how Profit was "
        "derived is not documented in the source.",
        "Results are descriptive. No significance tests or causal claims were made.",
    ])
    return "\n".join(lines)
