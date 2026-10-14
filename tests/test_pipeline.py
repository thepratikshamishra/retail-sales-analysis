"""End-to-end tests of run_analysis.main on the synthetic file."""
import json

import pytest

import pandas as pd

from run_analysis import main, save_tables
from tests.helpers import build_csv_text, order_row


def run(tmp_path, raw, *extra):
    out = tmp_path / "out"
    proc = tmp_path / "proc"
    code = main(["--raw-file", str(raw), "--output-dir", str(out),
                 "--processed-dir", str(proc), "--no-download", *extra])
    return code, out, proc


def test_changed_checksum_stops_the_run_with_a_clear_message(synthetic_csv, tmp_path, capsys):
    code, out, _ = run(tmp_path, synthetic_csv)
    assert code == 2
    assert "checksum" in capsys.readouterr().err
    assert not (out / "insights_report.md").exists()


def test_full_run_on_synthetic_data_writes_all_outputs(synthetic_csv, tmp_path):
    code, out, proc = run(tmp_path, synthetic_csv, "--allow-changed-data")
    assert code == 0
    for name in ["insights_report.md", "cleaning_report.md", "data_provenance.json"]:
        assert (out / name).stat().st_size > 0
    assert len(list((out / "figures").glob("*.png"))) == 15
    assert (out / "tables" / "category.csv").exists()
    assert (proc / "orders_clean.csv").exists() and (proc / "orders_rejected.csv").exists()

    stats = json.loads((out / "tables" / "summary_stats.json").read_text())
    assert stats["kpis"]["total_sales"] == pytest.approx(760)   # hand-calculated
    assert stats["kpis"]["total_profit"] == pytest.approx(111)
    assert stats["returns_stats"]["returned_orders"] == 1
    provenance = json.loads((out / "data_provenance.json").read_text())
    assert provenance["checksum_matches_expected"] is False      # synthetic != real file
    assert "Sales $760" in (out / "insights_report.md").read_text()


def test_duplicate_policy_drop_changes_totals(synthetic_csv, tmp_path):
    code, out, _ = run(tmp_path, synthetic_csv, "--allow-changed-data", "--duplicate-policy", "drop")
    assert code == 0
    stats = json.loads((out / "tables" / "summary_stats.json").read_text())
    assert stats["kpis"]["total_sales"] == pytest.approx(680)  # 760 - 80


def test_missing_file_returns_error_code(tmp_path, capsys):
    code, _, _ = run(tmp_path, tmp_path / "absent.csv")
    assert code == 2
    assert "not found" in capsys.readouterr().err


def test_malformed_file_returns_error_code(tmp_path, capsys):
    path = tmp_path / "bad.csv"
    lines = build_csv_text().splitlines()
    lines[2] = "2,only,three"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    code, _, _ = run(tmp_path, path, "--allow-changed-data")
    assert code == 2
    assert "malformed" in capsys.readouterr().err


def test_file_where_every_row_is_invalid_stops_cleanly_and_keeps_evidence(tmp_path, capsys):
    path = tmp_path / "allbad.csv"
    path.write_text(build_csv_text(
        order_rows=[order_row(1, "O1", "1/5/2020", "1/8/2020", sales=-5)]), encoding="utf-8")
    code, out, proc = run(tmp_path, path, "--allow-changed-data")
    assert code == 2
    assert "no valid order rows" in capsys.readouterr().err
    assert (out / "cleaning_report.md").exists()
    assert "Sales <= 0" in (proc / "orders_rejected.csv").read_text()
    assert not (out / "insights_report.md").exists()


def test_saved_tables_keep_full_precision(tmp_path):
    """Regression: tables were once written with 6 significant digits (2297200.86 -> 2.2972e+06)."""
    table = pd.DataFrame({"name": ["a"], "sales": [2297200.860312]})
    save_tables({"example": table, "stats": {"x": 1.5}}, tmp_path)
    back = pd.read_csv(tmp_path / "example.csv")
    assert back.loc[0, "sales"] == pytest.approx(2297200.860312, abs=1e-6)
    assert json.loads((tmp_path / "summary_stats.json").read_text())["stats"]["x"] == 1.5
