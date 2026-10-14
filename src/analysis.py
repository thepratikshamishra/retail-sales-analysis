"""Metric calculations. Every function takes the cleaned orders DataFrame and
returns plain tables/dicts; nothing here is hardcoded and nothing is plotted.

Definitions used throughout
---------------------------
sales            sum of the Sales column
profit           sum of the Profit column (can be negative)
profit_margin    profit / sales for a group  ("aggregate margin")
row_margin       Profit / Sales for ONE order line (see mean_row_margin below)
avg_order_value  sales / number of distinct orders

Aggregate margin and the average of row margins are different numbers: the
aggregate weights each line by its sales, the average treats a $5 line and a
$5,000 line equally. Both are reported and labelled.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

DISCOUNT_BINS = [-1.0, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
DISCOUNT_LABELS = ["0%", ">0-10%", ">10-20%", ">20-30%", ">30-50%", ">50%"]


def safe_divide(numerator, denominator):
    """Divide, returning NaN (not inf or an error) where the denominator is 0.

    Works for scalars and for aligned Series. A NaN input gives NaN.
    """
    num = np.asarray(numerator, dtype="float64")
    den = np.asarray(denominator, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(den == 0, np.nan, num / den)
    if result.ndim == 0:
        return float(result)
    index = getattr(numerator, "index", getattr(denominator, "index", None))
    return pd.Series(result, index=index)


def summarize(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Standard set of metrics for every group in `by`."""
    by = [by] if isinstance(by, str) else list(by)
    out = (
        df.groupby(by, observed=True)
        .agg(
            order_lines=("Order ID", "size"),
            orders=("Order ID", "nunique"),
            customers=("Customer ID", "nunique"),
            quantity=("Quantity", "sum"),
            sales=("Sales", "sum"),
            profit=("Profit", "sum"),
            avg_discount=("Discount", "mean"),
            loss_lines=("is_loss", "sum"),
        )
        .reset_index()
    )
    out["profit_margin"] = safe_divide(out["profit"], out["sales"])
    out["avg_order_value"] = safe_divide(out["sales"], out["orders"])
    out["loss_line_share"] = safe_divide(out["loss_lines"], out["order_lines"])
    out["sales_share"] = safe_divide(out["sales"], out["sales"].sum())
    return out


def top_and_bottom(table: pd.DataFrame, column: str, n: int = 10) -> pd.DataFrame:
    """The n highest and n lowest rows by `column`, highest first, no repeats."""
    ordered = table.sort_values(column, ascending=False)
    return pd.concat([ordered.head(n), ordered.tail(n)]).drop_duplicates()


# --------------------------------------------------------------------------
# overall
# --------------------------------------------------------------------------
def compute_kpis(df: pd.DataFrame) -> dict:
    total_sales = float(df["Sales"].sum())
    total_profit = float(df["Profit"].sum())
    n_orders = int(df["Order ID"].nunique())
    return {
        "date_start": df["Order Date"].min().strftime("%Y-%m-%d"),
        "date_end": df["Order Date"].max().strftime("%Y-%m-%d"),
        "order_lines": int(len(df)),
        "orders": n_orders,
        "customers": int(df["Customer ID"].nunique()),
        "products": int(df[["Product ID", "Product Name"]].drop_duplicates().shape[0]),
        "total_sales": total_sales,
        "total_profit": total_profit,
        "total_quantity": int(df["Quantity"].sum()),
        "aggregate_profit_margin": safe_divide(total_profit, total_sales),
        "mean_row_margin": float(df["row_margin"].mean()),
        "median_row_margin": float(df["row_margin"].median()),
        "avg_order_value": safe_divide(total_sales, n_orders),
        "avg_discount": float(df["Discount"].mean()),
        "loss_making_lines": int(df["is_loss"].sum()),
        "loss_making_line_share": safe_divide(int(df["is_loss"].sum()), len(df)),
        "possible_duplicate_lines": int(df["possible_duplicate"].sum())
        if "possible_duplicate" in df else 0,
    }


# --------------------------------------------------------------------------
# time
# --------------------------------------------------------------------------
def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = summarize(df, "order_year").sort_values("order_year").reset_index(drop=True)
    months = df.groupby("order_year")["order_month"].nunique()
    out["months_with_orders"] = out["order_year"].map(months)
    full_year = out["months_with_orders"] == 12
    comparable = full_year & full_year.shift(fill_value=False)
    # Growth is only meaningful between two complete years.
    out["sales_growth"] = out["sales"].pct_change().where(comparable)
    out["profit_growth"] = out["profit"].pct_change().where(comparable)
    return out


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = summarize(df, "order_month").sort_values("order_month").reset_index(drop=True)
    out["year"] = out["order_month"].dt.year
    out["month_num"] = out["order_month"].dt.month
    return out


def sales_by_year_month(df: pd.DataFrame) -> pd.DataFrame:
    """Year x month grid of total sales (NaN where a month has no orders)."""
    return df.pivot_table(index="order_year", columns="order_month_num",
                          values="Sales", aggfunc="sum")


def seasonality(df: pd.DataFrame) -> pd.DataFrame:
    """Average monthly sales for each calendar month across the years seen."""
    monthly = monthly_summary(df)
    out = (monthly.groupby("month_num")
           .agg(avg_monthly_sales=("sales", "mean"),
                avg_monthly_profit=("profit", "mean"),
                years_observed=("year", "nunique"))
           .reset_index())
    return out


# --------------------------------------------------------------------------
# product, category, region, segment
# --------------------------------------------------------------------------
def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    return summarize(df, "Category").sort_values("profit", ascending=False).reset_index(drop=True)


def subcategory_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = summarize(df, ["Category", "Sub-Category"])
    out["loss_making"] = out["profit"] < 0
    return out.sort_values("profit", ascending=False).reset_index(drop=True)


def region_summary(df: pd.DataFrame, people: pd.DataFrame | None = None) -> pd.DataFrame:
    out = summarize(df, "Region")
    if people is not None and not people.empty:
        out = out.merge(people.rename(columns={"Person": "person_listed_for_region"}),
                        on="Region", how="left")
    return out.sort_values("profit", ascending=False).reset_index(drop=True)


def state_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (summarize(df, ["Region", "State"])
            .sort_values("profit", ascending=False).reset_index(drop=True))


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    return summarize(df, "Segment").sort_values("sales", ascending=False).reset_index(drop=True)


def margin_matrix(df: pd.DataFrame, rows: str, cols: str) -> pd.DataFrame:
    """Aggregate profit margin for every rows x cols combination."""
    grouped = summarize(df, [rows, cols])
    return grouped.pivot(index=rows, columns=cols, values="profit_margin")


def product_summary(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["Product ID", "Product Name", "Category", "Sub-Category"]
    return summarize(df, keys).sort_values("profit", ascending=False).reset_index(drop=True)


def product_stats(products: pd.DataFrame) -> dict:
    losing = products[products["profit"] < 0]
    return {
        "products": int(len(products)),
        "loss_making_products": int(len(losing)),
        "loss_making_product_share": safe_divide(len(losing), len(products)),
        "total_loss_of_loss_making_products": float(losing["profit"].sum()),
        "profit_of_profitable_products": float(products.loc[products["profit"] > 0, "profit"].sum()),
    }


# --------------------------------------------------------------------------
# customers
# --------------------------------------------------------------------------
def customer_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = summarize(df, "Customer ID")
    names = df.groupby("Customer ID")["Customer Name"].first().rename("customer_name")
    dates = df.groupby("Customer ID")["Order Date"].agg(first_order="min", last_order="max")
    out = out.merge(names, on="Customer ID").merge(dates, on="Customer ID")
    return out.sort_values("sales", ascending=False).reset_index(drop=True)


def customer_concentration(customers: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """How concentrated sales are, plus the curve data (cumulative shares)."""
    ordered = customers.sort_values("sales", ascending=False).reset_index(drop=True)
    n = len(ordered)
    total = float(ordered["sales"].sum())
    top_20pct_n = max(1, math.ceil(0.2 * n))
    curve = pd.DataFrame({
        "customer_share": np.arange(1, n + 1) / n,
        "cumulative_sales_share": safe_divide(ordered["sales"].cumsum(), total),
    })
    losing = ordered[ordered["profit"] < 0]
    stats = {
        "customers": n,
        "top_10_customers_sales_share": safe_divide(float(ordered["sales"].head(10).sum()), total),
        "top_20pct_customers_n": top_20pct_n,
        "top_20pct_customers_sales_share": safe_divide(
            float(ordered["sales"].head(top_20pct_n).sum()), total),
        "median_orders_per_customer": float(ordered["orders"].median()),
        "customers_with_2plus_orders_share": safe_divide(int((ordered["orders"] >= 2).sum()), n),
        "loss_making_customers": int(len(losing)),
        "loss_making_customer_share": safe_divide(len(losing), n),
        "total_loss_of_loss_making_customers": float(losing["profit"].sum()),
    }
    return stats, curve


# --------------------------------------------------------------------------
# discounts
# --------------------------------------------------------------------------
def discount_band(discount: pd.Series) -> pd.Series:
    """Ordered categorical band for each discount (0 gets its own band)."""
    return pd.cut(discount.astype("float64"), bins=DISCOUNT_BINS,
                  labels=DISCOUNT_LABELS, right=True, ordered=True)


def discount_band_summary(df: pd.DataFrame) -> pd.DataFrame:
    work = df.assign(discount_band=discount_band(df["Discount"]))
    out = summarize(work, "discount_band").sort_values("discount_band").reset_index(drop=True)
    out["discount_band"] = out["discount_band"].astype(str)
    return out


def discount_level_summary(df: pd.DataFrame) -> pd.DataFrame:
    return summarize(df, "Discount").sort_values("Discount").reset_index(drop=True)


def discount_by_category(df: pd.DataFrame) -> pd.DataFrame:
    work = df.assign(discount_band=discount_band(df["Discount"]))
    out = summarize(work, ["Category", "discount_band"])
    out["discount_band"] = out["discount_band"].astype(str)
    return out.sort_values(["Category", "discount_band"]).reset_index(drop=True)


def discount_stats(df: pd.DataFrame, bands: pd.DataFrame) -> dict:
    """Spearman rank correlation of discount vs row margin, plus band facts.

    Spearman is used because margin is skewed with outliers and the discount
    takes only 12 distinct values; ranks make it robust to both.
    """
    ranks_d = df["Discount"].rank()
    ranks_m = df["row_margin"].rank()
    rho = float(ranks_d.corr(ranks_m)) if len(df) > 1 else float("nan")
    negative = bands[bands["profit_margin"] < 0]
    first_negative = negative.iloc[0]["discount_band"] if len(negative) else None
    return {
        "spearman_discount_vs_row_margin": rho,
        "first_band_with_negative_margin": first_negative,
        "lines_with_discount": int((df["Discount"] > 0).sum()),
        "share_of_lines_with_discount": safe_divide(int((df["Discount"] > 0).sum()), len(df)),
    }


# --------------------------------------------------------------------------
# returns
# --------------------------------------------------------------------------
def returns_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Returned vs not-returned orders, measured at order level."""
    per_order = df.groupby("Order ID").agg(
        is_returned=("is_returned", "max"), sales=("Sales", "sum"),
        profit=("Profit", "sum"), lines=("Order ID", "size"),
        avg_discount=("Discount", "mean"))
    out = per_order.groupby("is_returned").agg(
        orders=("sales", "size"), sales=("sales", "sum"), profit=("profit", "sum"),
        avg_order_value=("sales", "mean"), avg_lines_per_order=("lines", "mean"),
        avg_discount=("avg_discount", "mean")).reset_index()
    out["profit_margin"] = safe_divide(out["profit"], out["sales"])
    out["group"] = out["is_returned"].map({True: "Returned", False: "Not returned"})
    return out.drop(columns="is_returned")[
        ["group", "orders", "sales", "profit", "profit_margin",
         "avg_order_value", "avg_lines_per_order", "avg_discount"]]


def return_rate_by(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Share of orders that were returned, per group.

    An order counts once in every group it touches (e.g. an order with
    Furniture and Technology lines counts in both categories).
    """
    orders = df.groupby(by)["Order ID"].nunique().rename("orders")
    returned = (df[df["is_returned"]].groupby(by)["Order ID"].nunique()
                .rename("returned_orders"))
    out = pd.concat([orders, returned], axis=1).fillna(0).reset_index()
    out["returned_orders"] = out["returned_orders"].astype(int)
    out["return_rate"] = safe_divide(out["returned_orders"], out["orders"])
    sales = df.groupby(by)["Sales"].sum()
    returned_sales = df[df["is_returned"]].groupby(by)["Sales"].sum()
    out["share_of_sales_in_returned_orders"] = safe_divide(
        out[by].map(returned_sales).fillna(0), out[by].map(sales))
    return out.sort_values("return_rate", ascending=False).reset_index(drop=True)


def returns_stats(df: pd.DataFrame) -> dict:
    orders = df["Order ID"].nunique()
    returned = df.loc[df["is_returned"], "Order ID"].nunique()
    return {
        "orders": int(orders),
        "returned_orders": int(returned),
        "overall_return_rate": safe_divide(returned, orders),
        "share_of_sales_in_returned_orders": safe_divide(
            float(df.loc[df["is_returned"], "Sales"].sum()), float(df["Sales"].sum())),
    }


# --------------------------------------------------------------------------
# everything at once
# --------------------------------------------------------------------------
def run_all_analyses(orders: pd.DataFrame, people: pd.DataFrame | None = None,
                     returns_available: bool = True) -> dict:
    """Run every analysis. Keys ending in `_stats` (and `kpis`) are dicts;
    everything else is a DataFrame."""
    customers = customer_summary(orders)
    concentration, lorenz = customer_concentration(customers)
    products = product_summary(orders)
    bands = discount_band_summary(orders)

    results = {
        "kpis": compute_kpis(orders),
        "yearly": yearly_summary(orders),
        "monthly": monthly_summary(orders),
        "seasonality": seasonality(orders),
        "sales_year_month": sales_by_year_month(orders),
        "category": category_summary(orders),
        "subcategory": subcategory_summary(orders),
        "region": region_summary(orders, people),
        "state": state_summary(orders),
        "segment": segment_summary(orders),
        "margin_subcategory_region": margin_matrix(orders, "Sub-Category", "Region"),
        "customers": customers,
        "customer_stats": concentration,
        "lorenz": lorenz,
        "products": products,
        "product_stats": product_stats(products),
        "discount_bands": bands,
        "discount_levels": discount_level_summary(orders),
        "discount_by_category": discount_by_category(orders),
        "discount_stats": discount_stats(orders, bands),
        "returns_available": returns_available,
    }
    if returns_available:
        results.update({
            "returns_compare": returns_comparison(orders),
            "return_rate_region": return_rate_by(orders, "Region"),
            "return_rate_segment": return_rate_by(orders, "Segment"),
            "return_rate_category": return_rate_by(orders, "Category"),
            "returns_stats": returns_stats(orders),
        })
    return results
