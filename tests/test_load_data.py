import hashlib

import pytest

from src.load_data import (
    ORDERS_COLUMNS,
    PEOPLE_COLUMNS,
    RETURNS_COLUMNS,
    DataLoadError,
    download_raw_data,
    ensure_raw_data,
    read_sections,
    sha256_of_file,
)
from tests.helpers import build_csv_text, order_row


def write(tmp_path, text, name="data.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# ---- splitting the combined file ------------------------------------------
def test_splits_three_sections(sections):
    assert list(sections["orders"].columns) == ORDERS_COLUMNS
    assert list(sections["people"].columns) == PEOPLE_COLUMNS
    assert list(sections["returns"].columns) == RETURNS_COLUMNS
    assert len(sections["orders"]) == 7
    assert len(sections["people"]) == 2
    assert len(sections["returns"]) == 3


def test_people_and_returns_rows_do_not_leak_into_orders(sections):
    assert "Yes" not in set(sections["orders"]["Row ID"])
    assert "Anna" not in set(sections["orders"]["Row ID"])


def test_quoted_comma_in_product_name_is_kept(sections):
    assert "Chair, Large" in set(sections["orders"]["Product Name"])


def test_raw_values_stay_strings_and_unmodified(sections):
    # postal code "1040" is NOT zero-padded at load time; cleaning does that
    assert sections["orders"].loc[0, "Postal Code"] == "1040"
    assert sections["orders"].loc[2, "Postal Code"] == ""
    assert sections["orders"]["Sales"].map(type).eq(str).all()


def test_missing_people_and_returns_give_empty_frames(tmp_path):
    path = write(tmp_path, build_csv_text(include_people=False, include_returns=False))
    result = read_sections(path)
    assert len(result["orders"]) == 7
    assert result["people"].empty and result["returns"].empty
    assert list(result["returns"].columns) == RETURNS_COLUMNS


def test_blank_lines_between_sections_are_ignored(tmp_path):
    text = build_csv_text().replace("Person,Region", "\nPerson,Region")
    assert len(read_sections(write(tmp_path, text))["orders"]) == 7


def test_utf8_bom_is_accepted(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbf" + build_csv_text().encode("utf-8"))
    assert len(read_sections(path)["orders"]) == 7


# ---- bad input -------------------------------------------------------------
def test_missing_file_raises_clear_error(tmp_path):
    with pytest.raises(DataLoadError, match="not found"):
        read_sections(tmp_path / "nope.csv")


def test_empty_file_raises(tmp_path):
    with pytest.raises(DataLoadError):
        read_sections(write(tmp_path, ""))


def test_file_without_orders_header_raises(tmp_path):
    with pytest.raises(DataLoadError, match="before any recognised header"):
        read_sections(write(tmp_path, "a,b,c\n1,2,3\n"))


def test_orders_header_only_raises(tmp_path):
    with pytest.raises(DataLoadError, match="no data rows"):
        read_sections(write(tmp_path, ",".join(ORDERS_COLUMNS) + "\n"))


def test_wrong_field_count_reports_line_number(tmp_path):
    lines = build_csv_text().splitlines()
    lines[3] = "3,O2,only,three,fields"  # line 4 of the file
    with pytest.raises(DataLoadError, match=r"Line 4"):
        read_sections(write(tmp_path, "\n".join(lines) + "\n"))


def test_orders_header_with_missing_column_raises(tmp_path):
    header = [c for c in ORDERS_COLUMNS if c != "Profit"]
    with pytest.raises(DataLoadError, match="Missing columns.*Profit"):
        read_sections(write(tmp_path, ",".join(header) + "\n"))


def test_non_utf8_file_raises(tmp_path):
    path = tmp_path / "latin.csv"
    path.write_bytes(build_csv_text().encode("utf-8") + "caf\xe9\n".encode("latin-1"))
    with pytest.raises(DataLoadError, match="UTF-8"):
        read_sections(path)


# ---- checksum and download -------------------------------------------------
def test_sha256_of_file(tmp_path):
    path = write(tmp_path, "hello")
    assert sha256_of_file(path) == hashlib.sha256(b"hello").hexdigest()


def test_ensure_raw_data_accepts_matching_checksum(tmp_path):
    path = write(tmp_path, build_csv_text())
    info = ensure_raw_data(path, expected_sha256=sha256_of_file(path))
    assert info["checksum_matches_expected"] is True
    assert info["downloaded_this_run"] is False


def test_ensure_raw_data_rejects_changed_file(tmp_path):
    path = write(tmp_path, build_csv_text())
    with pytest.raises(DataLoadError, match="checksum"):
        ensure_raw_data(path, expected_sha256="0" * 64)


def test_ensure_raw_data_allows_changed_file_with_flag_and_records_it(tmp_path):
    path = write(tmp_path, build_csv_text())
    info = ensure_raw_data(path, expected_sha256="0" * 64, allow_changed=True)
    assert info["checksum_matches_expected"] is False


def test_ensure_raw_data_missing_file_with_downloads_disabled(tmp_path):
    with pytest.raises(DataLoadError, match="downloading is disabled"):
        ensure_raw_data(tmp_path / "x.csv", allow_download=False)


def test_download_saves_file_when_checksum_matches(tmp_path):
    source = write(tmp_path, build_csv_text(), "source.csv")
    dest = tmp_path / "out" / "copy.csv"
    digest = download_raw_data(dest, source.as_uri(), sha256_of_file(source))
    assert dest.read_bytes() == source.read_bytes()
    assert digest == sha256_of_file(source)


def test_download_with_wrong_checksum_does_not_overwrite_existing_file(tmp_path):
    source = write(tmp_path, build_csv_text(), "source.csv")
    dest = write(tmp_path, "GOOD LOCAL COPY", "dest.csv")
    with pytest.raises(DataLoadError, match="Checksum mismatch"):
        download_raw_data(dest, source.as_uri(), expected_sha256="0" * 64)
    assert dest.read_text() == "GOOD LOCAL COPY"


def test_download_failure_gives_fallback_instructions(tmp_path):
    missing = (tmp_path / "does_not_exist.csv").as_uri()
    with pytest.raises(DataLoadError, match="Fallback"):
        download_raw_data(tmp_path / "dest.csv", missing)
    assert not (tmp_path / "dest.csv").exists()


def test_download_of_empty_content_is_rejected(tmp_path):
    empty = write(tmp_path, "   \n", "empty.csv")
    with pytest.raises(DataLoadError, match="empty"):
        download_raw_data(tmp_path / "dest.csv", empty.as_uri(), expected_sha256=None)


def test_order_row_helper_matches_schema():
    assert len(order_row(1, "O1", "1/1/2020", "1/2/2020")) == len(ORDERS_COLUMNS)
