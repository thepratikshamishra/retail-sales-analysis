import pytest

from src.clean import prepare_data
from src.load_data import read_sections

from tests.helpers import build_csv_text


@pytest.fixture
def synthetic_csv(tmp_path):
    path = tmp_path / "synthetic.csv"
    path.write_text(build_csv_text(), encoding="utf-8")
    return path


@pytest.fixture
def sections(synthetic_csv):
    return read_sections(synthetic_csv)


@pytest.fixture
def cleaned(sections):
    return prepare_data(sections)
