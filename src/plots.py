"""Charts. Every chart is drawn from a table computed in analysis.py; nothing
is typed in by hand. Style: white surface, one blue for amounts, red for
losses (negative values), light grid, labels in dark grey.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files only; no display needed
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from .analysis import top_and_bottom  # noqa: E402

BLUE = "#2a78d6"
RED = "#e34948"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
GRID = "#e6e5e0"
SURFACE = "#fcfcfb"
NEUTRAL = "#f0efec"
SEQUENTIAL = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#2a78d6", "#0d366b"])
DIVERGING = LinearSegmentedColormap.from_list("div_red_blue", [RED, NEUTRAL, BLUE])


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_SOFT, "axes.titlecolor": INK,
        "xtick.color": INK_SOFT, "ytick.color": INK_SOFT, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "font.size": 9.5, "axes.titlesize": 10.5,
        "axes.titleweight": "bold", "axes.titlelocation": "left",
    })


def _money(value: float, _pos=None) -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e6:
        return f"{sign}${v / 1e6:.2f}M"
    if v >= 1e3:
        return f"{sign}${v / 1e3:.0f}K"
    return f"{sign}${v:.0f}"


def _percent(value: float, _pos=None) -> str:
    return f"{value * 100:.0f}%"


MONEY_AXIS = FuncFormatter(_money)
PERCENT_AXIS = FuncFormatter(_percent)


def _signed_colors(values) -> list[str]:
    return [BLUE if v >= 0 else RED for v in values]


def _sign_legend(fig, values) -> None:
    """Blue/red key in the title row. Only drawn when some value is negative;
    a chart with a single colour needs no legend."""
    if not any(v < 0 for v in values):
        return
    fig.legend(handles=[Patch(color=BLUE, label="Profit (>= 0)"),
                        Patch(color=RED, label="Loss (< 0)")],
               loc="upper right", bbox_to_anchor=(0.995, 1 - 0.05 / fig.get_figheight()),
               ncol=2, frameon=False, fontsize=8)


def _save(fig, path: Path, title: str, subtitle: str, source_note: str) -> Path:
    height = fig.get_figheight()
    fig.suptitle(title, x=0.01, y=1 - 0.08 / height, ha="left", va="top",
                 fontsize=13, fontweight="bold")
    fig.text(0.01, 1 - 0.42 / height, subtitle, fontsize=9, color=INK_SOFT,
             ha="left", va="top")
    fig.text(0.01, 0.07 / height, source_note, fontsize=7, color=INK_SOFT,
             ha="left", va="bottom")
    fig.tight_layout(rect=[0, 0.4 / height, 1, 1 - 0.75 / height])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _hbar(ax, labels, values, fmt=_money, colors=None, invert=True) -> None:
    values = list(values)
    y = np.arange(len(values))
    bars = ax.barh(y, values, color=colors or _signed_colors(values), height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    if invert:  # first row at the top; skip for a panel sharing y with an inverted one
        ax.invert_yaxis()
    ax.bar_label(bars, labels=[fmt(v) for v in values], padding=3, fontsize=8, color=INK)
    ax.axvline(0, color=INK_SOFT, lw=0.8)
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.18)


def _label(value) -> str:
    if isinstance(value, (int, float, np.integer, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _shorten(text: str, width: int = 46) -> str:
    return textwrap.shorten(str(text), width=width, placeholder="...")


# --------------------------------------------------------------------------
# generic two-panel chart: sales (left) and profit (right) per group
# --------------------------------------------------------------------------
def plot_sales_profit_panels(table: pd.DataFrame, label_col: str, path: Path, title: str,
                             subtitle: str, source_note: str) -> Path:
    _style()
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.8))
    labels = [f"{_label(row[label_col])}\nmargin {row['profit_margin'] * 100:.1f}%"
              for _, row in table.iterrows()]
    x = np.arange(len(table))
    for ax, column, name in [(left, "sales", "Sales"), (right, "profit", "Profit")]:
        values = table[column].to_numpy()
        colors = [BLUE] * len(values) if column == "sales" else _signed_colors(values)
        bars = ax.bar(x, values, color=colors, width=0.6)
        ax.bar_label(bars, labels=[_money(v) for v in values], padding=3, fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8.5)
        ax.yaxis.set_major_formatter(MONEY_AXIS)
        ax.axhline(0, color=INK_SOFT, lw=0.8)
        ax.grid(axis="x", visible=False)
        ax.margins(y=0.15)
        ax.set_title(f"{name} (USD)")
    _sign_legend(fig, table["profit"])
    return _save(fig, path, title, subtitle, source_note)


# --------------------------------------------------------------------------
# time
# --------------------------------------------------------------------------
def plot_monthly_trend(monthly: pd.DataFrame, path: Path, source_note: str) -> Path:
    _style()
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10.5, 6.2), sharex=True)
    top.plot(monthly["order_month"], monthly["sales"], color=BLUE, lw=2)
    bottom.plot(monthly["order_month"], monthly["profit"], color=BLUE, lw=2)
    bottom.axhline(0, color=INK_SOFT, lw=0.8)
    for ax, column, name in [(top, "sales", "Monthly sales (USD)"),
                             (bottom, "profit", "Monthly profit (USD)")]:
        peak = monthly.loc[monthly[column].idxmax()]
        low = monthly.loc[monthly[column].idxmin()]
        for point, tag in [(peak, "high"), (low, "low")]:
            ax.scatter([point["order_month"]], [point[column]], s=45, color=BLUE,
                       edgecolor=SURFACE, linewidth=1.5, zorder=3)
            ax.annotate(f"{point['order_month']:%b %Y} {tag}: {_money(point[column])}",
                        (point["order_month"], point[column]), textcoords="offset points",
                        xytext=(6, 8 if tag == "high" else -14), fontsize=8, color=INK)
        ax.yaxis.set_major_formatter(MONEY_AXIS)
        ax.set_title(name)
        ax.margins(y=0.2)
    bottom.xaxis.set_major_locator(mdates.YearLocator())
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    return _save(fig, path, "Monthly sales and profit",
                 f"{monthly['order_month'].min():%b %Y} to {monthly['order_month'].max():%b %Y}; "
                 "one point per calendar month; highest and lowest month labelled", source_note)


def plot_sales_heatmap(grid: pd.DataFrame, path: Path, source_note: str) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(10.5, 3.8))
    shown = (grid / 1000.0).copy()
    shown.columns = [pd.Timestamp(2000, int(m), 1).strftime("%b") for m in shown.columns]
    sns.heatmap(shown, annot=True, fmt=".0f", cmap=SEQUENTIAL, linewidths=1,
                linecolor=SURFACE, cbar_kws={"label": "Sales (USD thousands)"}, ax=ax)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.grid(False)
    return _save(fig, path, "Sales by year and month",
                 "Total sales in USD thousands; darker = higher", source_note)


# --------------------------------------------------------------------------
# product / category
# --------------------------------------------------------------------------
def plot_subcategory_profit(sub: pd.DataFrame, path: Path, source_note: str) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    _hbar(ax, sub["Sub-Category"], sub["profit"])
    ax.xaxis.set_major_formatter(MONEY_AXIS)
    ax.set_title("Total profit by sub-category (USD)")
    _sign_legend(fig, sub["profit"])
    return _save(fig, path, "Sub-category profit",
                 "All sub-categories, highest profit first; red bars are loss-making", source_note)


def plot_products_top_bottom(products: pd.DataFrame, path: Path, source_note: str,
                             n: int = 10) -> Path:
    _style()
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10.5, 8.6))
    best = products.sort_values("profit", ascending=False).head(n)
    worst = products.sort_values("profit").head(n)
    for ax, frame, name in [(top, best, f"Top {n} products by profit"),
                            (bottom, worst, f"{n} largest product losses")]:
        _hbar(ax, [_shorten(v) for v in frame["Product Name"]], frame["profit"])
        ax.xaxis.set_major_formatter(MONEY_AXIS)
        ax.set_title(name)
    _sign_legend(fig, pd.concat([best["profit"], worst["profit"]]))
    return _save(fig, path, "Product profit: best and worst",
                 "Total profit per Product ID + name over the whole period (USD)", source_note)


# --------------------------------------------------------------------------
# geography
# --------------------------------------------------------------------------
def plot_state_profit(states: pd.DataFrame, path: Path, source_note: str, n: int = 10) -> Path:
    _style()
    chosen = top_and_bottom(states, "profit", n)
    fig, ax = plt.subplots(figsize=(9.5, 7.2))
    _hbar(ax, chosen["State"], chosen["profit"])
    ax.xaxis.set_major_formatter(MONEY_AXIS)
    ax.set_title(f"Total profit (USD): top {n} and bottom {n} states")
    _sign_legend(fig, chosen["profit"])
    return _save(fig, path, "State profit",
                 f"{len(states)} states in total; highest and lowest {n} shown", source_note)


def plot_margin_heatmap(matrix: pd.DataFrame, path: Path, source_note: str) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(8.5, 7.4))
    limit = float(np.nanmax(np.abs(matrix.to_numpy())))
    sns.heatmap(matrix, annot=True, fmt=".1%", cmap=DIVERGING, center=0, vmin=-limit,
                vmax=limit, linewidths=1, linecolor=SURFACE, annot_kws={"fontsize": 8},
                cbar_kws={"label": "Aggregate profit margin"}, ax=ax)
    ax.collections[0].colorbar.ax.yaxis.set_major_formatter(PERCENT_AXIS)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.grid(False)
    return _save(fig, path, "Profit margin by sub-category and region",
                 "Aggregate margin = total profit / total sales in each cell; "
                 "red = loss, blue = profit", source_note)


# --------------------------------------------------------------------------
# customers
# --------------------------------------------------------------------------
def plot_top_customers(customers: pd.DataFrame, path: Path, source_note: str, n: int = 10) -> Path:
    _style()
    top = customers.sort_values("sales", ascending=False).head(n)
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    labels = list(top["customer_name"])
    _hbar(left, labels, top["sales"], colors=[BLUE] * len(top))
    left.xaxis.set_major_formatter(MONEY_AXIS)
    left.set_title("Sales (USD)")
    _hbar(right, labels, top["profit"], invert=False)  # y axis is shared with `left`
    right.xaxis.set_major_formatter(MONEY_AXIS)
    right.set_title("Profit (USD) of the same customers")
    _sign_legend(fig, top["profit"])
    return _save(fig, path, f"Top {n} customers by sales",
                 "Ranked by total sales; the right panel shows whether they were profitable",
                 source_note)


def plot_customer_concentration(lorenz: pd.DataFrame, stats: dict, path: Path,
                                source_note: str) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(7.5, 6))
    x = np.concatenate([[0], lorenz["customer_share"]])
    y = np.concatenate([[0], lorenz["cumulative_sales_share"]])
    ax.plot(x, y, color=BLUE, lw=2, label="Actual (customers ranked by sales)")
    ax.plot([0, 1], [0, 1], color=INK_SOFT, lw=1, ls="--", label="If every customer bought equally")
    share20 = stats["top_20pct_customers_sales_share"]
    ax.scatter([0.2], [share20], s=45, color=BLUE, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.annotate(f"Top 20% of customers = {share20 * 100:.1f}% of sales", (0.2, share20),
                textcoords="offset points", xytext=(10, -22), fontsize=8.5)
    ax.xaxis.set_major_formatter(PERCENT_AXIS)
    ax.yaxis.set_major_formatter(PERCENT_AXIS)
    ax.set_xlabel("Cumulative share of customers (highest sales first)")
    ax.set_ylabel("Cumulative share of sales")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    return _save(fig, path, "Customer sales concentration",
                 f"{stats['customers']:,} customers; closer to the dashed line = more even",
                 source_note)


# --------------------------------------------------------------------------
# discounts
# --------------------------------------------------------------------------
def plot_discount_bands(bands: pd.DataFrame, path: Path, source_note: str) -> Path:
    _style()
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.8))
    labels = [f"{row.discount_band}\n(n={row.order_lines:,})" for row in bands.itertuples()]
    x = np.arange(len(bands))
    margins = bands["profit_margin"].to_numpy()
    bars = left.bar(x, margins, color=_signed_colors(margins), width=0.6)
    left.bar_label(bars, labels=[f"{m * 100:.1f}%" for m in margins], padding=3, fontsize=8)
    left.yaxis.set_major_formatter(PERCENT_AXIS)
    left.axhline(0, color=INK_SOFT, lw=0.8)
    left.set_title("Aggregate profit margin")
    shares = bands["loss_line_share"].to_numpy()
    bars = right.bar(x, shares, color=BLUE, width=0.6)
    right.bar_label(bars, labels=[f"{s * 100:.0f}%" for s in shares], padding=3, fontsize=8)
    right.yaxis.set_major_formatter(PERCENT_AXIS)
    right.set_title("Share of order lines with negative profit")
    for ax in (left, right):
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8.5)
        ax.set_xlabel("Discount band (n = order lines)")
        ax.grid(axis="x", visible=False)
        ax.margins(y=0.15)
    _sign_legend(fig, margins)
    return _save(fig, path, "Discount level vs profitability",
                 "Order lines grouped by discount; right-closed bands, 0% shown separately",
                 source_note)


def plot_discount_scatter(orders: pd.DataFrame, levels: pd.DataFrame, path: Path,
                          source_note: str) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(9.5, 6))
    rng = np.random.default_rng(42)  # fixed seed: jitter only, so the picture is repeatable
    jitter = rng.uniform(-0.008, 0.008, size=len(orders))
    ax.scatter(orders["Discount"] + jitter, orders["row_margin"], s=8, alpha=0.25,
               color=BLUE, linewidths=0, label="Individual order lines")
    ax.scatter(levels["Discount"], levels["profit_margin"], s=70, color=INK,
               edgecolor=SURFACE, linewidth=1.5, zorder=3,
               label="Aggregate margin at each discount level")
    ax.axhline(0, color=RED, lw=1)
    ax.xaxis.set_major_formatter(PERCENT_AXIS)
    ax.yaxis.set_major_formatter(PERCENT_AXIS)
    ax.set_xlabel("Discount")
    ax.set_ylabel("Profit margin (Profit / Sales)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    return _save(fig, path, "Discount vs profit margin, every order line",
                 f"{len(orders):,} lines; x-position jittered by up to 0.8 percentage points "
                 "for visibility only; red line = break-even", source_note)


# --------------------------------------------------------------------------
# returns
# --------------------------------------------------------------------------
def plot_returns_overview(region: pd.DataFrame, segment: pd.DataFrame, category: pd.DataFrame,
                          overall_rate: float, path: Path, source_note: str) -> Path:
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.6), sharey=True)
    for ax, table, name in zip(axes, [region, segment, category],
                               ["Region", "Segment", "Category"]):
        col = table.columns[0]
        x = np.arange(len(table))
        bars = ax.bar(x, table["return_rate"], color=BLUE, width=0.6)
        ax.bar_label(bars, labels=[f"{v * 100:.1f}%" for v in table["return_rate"]],
                     padding=3, fontsize=8)
        ax.axhline(overall_rate, color=INK_SOFT, lw=1, ls="--")
        ax.set_xticks(x)
        ax.set_xticklabels(table[col], fontsize=8.5)
        ax.set_title(f"By {name.lower()}")
        ax.yaxis.set_major_formatter(PERCENT_AXIS)
        ax.grid(axis="x", visible=False)
        ax.margins(y=0.2)
    axes[0].set_ylabel("Share of orders returned")
    return _save(fig, path, "Return rate by region, segment and category",
                 f"Return rate = returned orders / orders; dashed line = overall {overall_rate * 100:.1f}%. "
                 "An order counts in every category it contains", source_note)


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def generate_all_charts(results: dict, orders: pd.DataFrame, out_dir: str | Path,
                        source_note: str) -> tuple[list[Path], dict[str, str]]:
    """Draw every chart. A failing chart is reported, not hidden, and does not
    stop the others. Returns (files_created, {chart_name: error_message})."""
    out_dir = Path(out_dir)
    k = results["kpis"]
    span = f"{k['date_start']} to {k['date_end']}"
    jobs = {
        "01_yearly_sales_profit": lambda p: plot_sales_profit_panels(
            results["yearly"], "order_year", p, "Sales and profit by year",
            f"Orders {span}; margin = profit / sales", source_note),
        "02_monthly_trend": lambda p: plot_monthly_trend(results["monthly"], p, source_note),
        "03_heatmap_sales_year_month": lambda p: plot_sales_heatmap(
            results["sales_year_month"], p, source_note),
        "04_category_sales_profit": lambda p: plot_sales_profit_panels(
            results["category"], "Category", p, "Sales and profit by category",
            f"Orders {span}; margin = profit / sales", source_note),
        "05_subcategory_profit": lambda p: plot_subcategory_profit(
            results["subcategory"], p, source_note),
        "06_region_sales_profit": lambda p: plot_sales_profit_panels(
            results["region"], "Region", p, "Sales and profit by region",
            f"Orders {span}; margin = profit / sales", source_note),
        "07_state_profit": lambda p: plot_state_profit(results["state"], p, source_note),
        "08_segment_sales_profit": lambda p: plot_sales_profit_panels(
            results["segment"], "Segment", p, "Sales and profit by customer segment",
            f"Orders {span}; margin = profit / sales", source_note),
        "09_top_customers": lambda p: plot_top_customers(results["customers"], p, source_note),
        "10_customer_concentration": lambda p: plot_customer_concentration(
            results["lorenz"], results["customer_stats"], p, source_note),
        "11_discount_bands": lambda p: plot_discount_bands(
            results["discount_bands"], p, source_note),
        "12_discount_scatter": lambda p: plot_discount_scatter(
            orders, results["discount_levels"], p, source_note),
        "13_heatmap_margin_subcategory_region": lambda p: plot_margin_heatmap(
            results["margin_subcategory_region"], p, source_note),
        "14_products_top_bottom": lambda p: plot_products_top_bottom(
            results["products"], p, source_note),
    }
    if results.get("returns_available"):
        jobs["15_returns_overview"] = lambda p: plot_returns_overview(
            results["return_rate_region"], results["return_rate_segment"],
            results["return_rate_category"],
            results["returns_stats"]["overall_return_rate"], p, source_note)

    created: list[Path] = []
    failed: dict[str, str] = {}
    for name, draw in jobs.items():
        try:
            created.append(draw(out_dir / f"{name}.png"))
        except Exception as exc:  # noqa: BLE001 - reported to the user below
            plt.close("all")
            failed[name] = f"{type(exc).__name__}: {exc}"
    return created, failed
