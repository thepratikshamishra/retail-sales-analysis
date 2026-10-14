"""Run the whole analysis with one command:

    python run_analysis.py

Steps: download/verify data -> split sections -> clean -> analyse -> save
tables, charts and reports under outputs/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis import run_all_analyses
from src.clean import CleaningError, prepare_data
from src.load_data import DEFAULT_RAW_PATH, DataLoadError, ensure_raw_data, read_sections
from src.plots import generate_all_charts
from src.report import build_insights

SOURCE_NOTE_TEMPLATE = (
    "Source: Sample Superstore (fictional retailer; licence not independently verified), "
    "orders {start} to {end}. All values computed by this project's code."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Retail sales analysis on Sample Superstore")
    p.add_argument("--raw-file", default=str(DEFAULT_RAW_PATH),
                   help="path to the raw CSV (downloaded here if missing)")
    p.add_argument("--output-dir", default="outputs", help="where tables, charts and reports go")
    p.add_argument("--processed-dir", default=str(Path("data") / "processed"),
                   help="where the cleaned row-level data and rejected rows go")
    p.add_argument("--refresh-download", action="store_true",
                   help="download the file again even if it exists")
    p.add_argument("--no-download", action="store_true",
                   help="never download; fail if the raw file is missing")
    p.add_argument("--allow-changed-data", action="store_true",
                   help="accept a file whose SHA-256 differs from the one this project was built on")
    p.add_argument("--duplicate-policy", choices=["flag", "drop"], default="flag",
                   help="rows identical except Row ID: keep and flag (default) or drop")
    return p.parse_args(argv)


def _to_builtin(obj):
    """Make numpy/pandas scalars JSON-friendly."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float) and np.isnan(obj):
        return None
    raise TypeError(f"Cannot serialise {type(obj)}")


def save_tables(results: dict, table_dir: Path) -> list[Path]:
    """DataFrames -> CSV (one per table); dict results -> summary_stats.json."""
    table_dir.mkdir(parents=True, exist_ok=True)
    written, stats = [], {}
    for name, value in results.items():
        if isinstance(value, pd.DataFrame):
            keep_index = not isinstance(value.index, pd.RangeIndex)
            path = table_dir / f"{name}.csv"
            # round(6) only removes floating-point noise; it does not drop real digits
            floats = {c: 6 for c in value.select_dtypes("float").columns}
            value.round(floats).to_csv(path, index=keep_index)
            written.append(path)
        elif isinstance(value, dict):
            stats[name] = value
    path = table_dir / "summary_stats.json"
    path.write_text(json.dumps(stats, indent=2, default=_to_builtin), encoding="utf-8")
    written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir)
    processed_dir = Path(args.processed_dir)

    try:
        print("1/5 Checking raw data ...")
        provenance = ensure_raw_data(
            args.raw_file, refresh=args.refresh_download,
            allow_changed=args.allow_changed_data, allow_download=not args.no_download)
        print(f"    {provenance['local_path']}  sha256 matches expected: "
              f"{provenance['checksum_matches_expected']}")
        print("2/5 Splitting Orders / People / Returns ...")
        sections = read_sections(args.raw_file)
        print("    " + ", ".join(f"{k}: {len(v):,} rows" for k, v in sections.items()))
        print("3/5 Cleaning ...")
        cleaned = prepare_data(sections, duplicate_policy=args.duplicate_policy)
    except (DataLoadError, CleaningError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 2

    orders = cleaned.orders
    print(f"    {len(orders):,} order lines kept, {len(cleaned.rejected):,} rejected")

    if orders.empty:
        # Nothing to analyse: save the evidence, then stop with a clear message.
        out_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "cleaning_report.md").write_text(
            cleaned.report.to_markdown(), encoding="utf-8")
        cleaned.rejected.to_csv(processed_dir / "orders_rejected.csv", index=False)
        print("\nERROR: no valid order rows remain after cleaning, so there is nothing "
              "to analyse. See "
              f"{out_dir / 'cleaning_report.md'} and {processed_dir / 'orders_rejected.csv'} "
              "for the reasons rows were rejected.", file=sys.stderr)
        return 2

    print("4/5 Analysing ...")
    results = run_all_analyses(orders, cleaned.people, cleaned.returns_available)
    k = results["kpis"]
    source_note = SOURCE_NOTE_TEMPLATE.format(start=k["date_start"], end=k["date_end"])

    out_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    tables = save_tables(results, out_dir / "tables")
    (out_dir / "cleaning_report.md").write_text(cleaned.report.to_markdown(), encoding="utf-8")
    (out_dir / "data_provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8")
    (out_dir / "insights_report.md").write_text(
        build_insights(results, source_note), encoding="utf-8")
    orders.to_csv(processed_dir / "orders_clean.csv", index=False)
    cleaned.rejected.to_csv(processed_dir / "orders_rejected.csv", index=False)

    print("5/5 Drawing charts ...")
    charts, failed = generate_all_charts(results, orders, out_dir / "figures", source_note)

    print("\nDone.")
    print(f"  Sales {k['total_sales']:,.2f} | Profit {k['total_profit']:,.2f} | "
          f"Quantity {k['total_quantity']:,} | Aggregate margin {k['aggregate_profit_margin']:.2%}")
    print(f"  {len(tables)} table files -> {out_dir / 'tables'}")
    print(f"  {len(charts)} charts      -> {out_dir / 'figures'}")
    print(f"  Reports: {out_dir / 'insights_report.md'}, {out_dir / 'cleaning_report.md'}")
    if failed:
        print("\nWARNING: some charts failed:", file=sys.stderr)
        for name, message in failed.items():
            print(f"  {name}: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
