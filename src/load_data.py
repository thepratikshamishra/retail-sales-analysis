"""Download, verify and read the Sample Superstore CSV.

The upstream file is not one table. It is three CSV blocks stacked in one file:

    Orders   header starts with "Row ID" (21 columns, the sales lines)
    People   header "Person,Region"
    Returns  header "Returned,Order ID"

Reading the whole file with one pd.read_csv would treat the People and Returns
rows as broken order lines (806 rows that are almost entirely empty). This
module splits the blocks first and returns each one as its own DataFrame of
raw strings. Nothing is converted or cleaned here, so the source stays intact.
"""
from __future__ import annotations

import csv
import hashlib
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

DATA_URL = (
    "https://raw.githubusercontent.com/leonism/sample-superstore/"
    "master/data/superstore.csv"
)
# SHA-256 of the file as inspected when this project was built. If the upstream
# file changes, the check fails loudly instead of silently analysing new data.
EXPECTED_SHA256 = "af443ca30d732c886f7a1d603f9492f98e9a88c268d47cbc146fe758b1f5d65d"
DEFAULT_RAW_PATH = Path("data") / "raw" / "superstore.csv"

ORDERS_COLUMNS = [
    "Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode",
    "Customer ID", "Customer Name", "Segment", "Country", "City", "State",
    "Postal Code", "Region", "Product ID", "Category", "Sub-Category",
    "Product Name", "Sales", "Quantity", "Discount", "Profit",
]
PEOPLE_COLUMNS = ["Person", "Region"]
RETURNS_COLUMNS = ["Returned", "Order ID"]

_SECTION_HEADERS = {
    "orders": ORDERS_COLUMNS,
    "people": PEOPLE_COLUMNS,
    "returns": RETURNS_COLUMNS,
}


class DataLoadError(Exception):
    """The data could not be downloaded, verified or parsed."""


def sha256_of_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manual_download_help(url: str, dest: Path) -> str:
    return (
        "Fallback: download the file yourself and save it as\n"
        f"    {dest}\n"
        f"from\n    {url}\n"
        "(browser 'Save as...' or: curl -L -o <path> <url>), then run the "
        "pipeline again. If the file differs from the version this project "
        "was built on you will be told, and can accept it with "
        "--allow-changed-data."
    )


def download_raw_data(
    dest: str | Path,
    url: str = DATA_URL,
    expected_sha256: str | None = EXPECTED_SHA256,
    allow_changed: bool = False,
    timeout: int = 60,
) -> str:
    """Download `url` to `dest` and return the SHA-256 of what was saved.

    The file is only written if the checksum matches (or allow_changed=True),
    so a failed or unexpected download never overwrites a good local copy.
    """
    dest = Path(dest)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            content = response.read()
    except OSError as exc:  # URLError, HTTPError and timeouts are all OSErrors
        raise DataLoadError(
            f"Could not download {url}: {exc}\n{manual_download_help(url, dest)}"
        ) from exc

    if not content.strip():
        raise DataLoadError(f"The download from {url} was empty.")

    actual = hashlib.sha256(content).hexdigest()
    if expected_sha256 and actual != expected_sha256 and not allow_changed:
        raise DataLoadError(
            "Checksum mismatch: the downloaded file is not the version this "
            "project was built on.\n"
            f"  expected {expected_sha256}\n  got      {actual}\n"
            "The upstream file may have changed. Nothing was saved. Inspect "
            "it, then re-run with --allow-changed-data if you accept it."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    partial.write_bytes(content)
    partial.replace(dest)
    return actual


def ensure_raw_data(
    path: str | Path = DEFAULT_RAW_PATH,
    url: str = DATA_URL,
    expected_sha256: str | None = EXPECTED_SHA256,
    refresh: bool = False,
    allow_changed: bool = False,
    allow_download: bool = True,
) -> dict:
    """Make sure the raw file exists and verify it. Returns provenance info."""
    path = Path(path)
    downloaded = False
    if refresh or not path.exists():
        if not allow_download:
            raise DataLoadError(
                f"Data file not found: {path} (downloading is disabled).\n"
                + manual_download_help(url, path)
            )
        download_raw_data(path, url, expected_sha256, allow_changed)
        downloaded = True

    actual = sha256_of_file(path)
    matches = None if not expected_sha256 else actual == expected_sha256
    if matches is False and not allow_changed:
        raise DataLoadError(
            f"{path} does not match the checksum this project was built on.\n"
            f"  expected {expected_sha256}\n  got      {actual}\n"
            "Re-run with --allow-changed-data if the change is intended."
        )
    return {
        "source_url": url,
        "local_path": str(path),
        "downloaded_this_run": downloaded,
        "size_bytes": path.stat().st_size,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual,
        "checksum_matches_expected": matches,
    }


def _identify_header(cells: list[str]) -> str | None:
    """Return the section name if `cells` is a section header row."""
    for name, columns in _SECTION_HEADERS.items():
        if cells == columns:
            return name
    if cells and cells[0] == "Row ID":
        missing = [c for c in ORDERS_COLUMNS if c not in cells]
        extra = [c for c in cells if c not in ORDERS_COLUMNS]
        raise DataLoadError(
            "The Orders header does not match the expected schema. "
            f"Missing columns: {missing}; unexpected columns: {extra}."
        )
    return None


def read_sections(path: str | Path) -> dict[str, pd.DataFrame]:
    """Split the combined file into raw-string DataFrames.

    Returns {"orders", "people", "returns"}. Orders is required. People and
    Returns come back empty (with their columns) if the file has no such block.
    """
    path = Path(path)
    if not path.is_file():
        raise DataLoadError(f"Data file not found: {path}")

    rows: dict[str, list[list[str]]] = {name: [] for name in _SECTION_HEADERS}
    seen: set[str] = set()
    current: str | None = None

    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            for row in reader:
                cells = [cell.strip() for cell in row]
                if not any(cells):
                    continue  # blank separator line
                header = _identify_header(cells)
                if header:
                    current = header
                    seen.add(header)
                    continue
                if current is None:
                    raise DataLoadError(
                        f"Line {reader.line_num}: data found before any "
                        "recognised header row. Is this the Superstore file?"
                    )
                expected = len(_SECTION_HEADERS[current])
                if len(row) != expected:
                    raise DataLoadError(
                        f"Line {reader.line_num}: a {current} row has "
                        f"{len(row)} fields, expected {expected}. "
                        "The file looks malformed."
                    )
                rows[current].append(row)  # original strings, not stripped
    except UnicodeDecodeError as exc:
        raise DataLoadError(f"{path} is not valid UTF-8 text: {exc}") from exc
    except csv.Error as exc:
        raise DataLoadError(f"{path} could not be parsed as CSV: {exc}") from exc

    if "orders" not in seen:
        raise DataLoadError(
            f"No Orders header (starting with 'Row ID') found in {path}."
        )
    if not rows["orders"]:
        raise DataLoadError(f"The Orders section of {path} has no data rows.")

    return {
        name: pd.DataFrame(rows[name], columns=_SECTION_HEADERS[name])
        for name in _SECTION_HEADERS
    }
