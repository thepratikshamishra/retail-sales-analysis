"""Chart tests check that every chart is produced as a real PNG and that a
failing chart is reported instead of hidden. They do not judge how a chart
looks - that was checked by eye on the real outputs."""
from pathlib import Path

import pandas as pd
import pytest

from src.analysis import run_all_analyses
from src.plots import generate_all_charts

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SOURCE_NOTE = "test source note"


@pytest.fixture
def results(cleaned):
    return run_all_analyses(cleaned.orders, cleaned.people, cleaned.returns_available)


def test_all_charts_are_written_as_png(results, cleaned, tmp_path):
    created, failed = generate_all_charts(results, cleaned.orders, tmp_path, SOURCE_NOTE)
    assert failed == {}
    assert len(created) == 15
    for path in created:
        assert path.exists() and path.stat().st_size > 2000
        assert Path(path).read_bytes()[:8] == PNG_SIGNATURE


def test_returns_chart_is_skipped_when_no_returns(cleaned, tmp_path):
    results = run_all_analyses(cleaned.orders, cleaned.people, returns_available=False)
    created, failed = generate_all_charts(results, cleaned.orders, tmp_path, SOURCE_NOTE)
    assert failed == {}
    assert len(created) == 14
    assert not any("returns" in p.name for p in created)


def test_one_failing_chart_is_reported_and_others_still_drawn(results, cleaned, tmp_path):
    broken = dict(results)
    broken["yearly"] = pd.DataFrame()  # chart 01 cannot be drawn from an empty table
    created, failed = generate_all_charts(broken, cleaned.orders, tmp_path, SOURCE_NOTE)
    assert "01_yearly_sales_profit" in failed
    assert len(created) == 14
