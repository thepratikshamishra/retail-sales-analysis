"""Synthetic test data. Everything here is INVENTED for testing and is not
Superstore data. Values are small so expected results can be checked by hand.

SYNTHETIC DATASET (7 order lines)
 row  order  customer  region  category         product   sales qty disc  profit
 1    O1     Alice     West    Furniture        Chair      100   1   0.0    20   (postal code "1040")
 2    O1     Alice     West    Technology       Phone      200   2   0.0    50
 3    O2     Bob       East    Furniture        Chair      100   1   0.2   -10   (postal code missing)
 4    O3     Bob       East    Office Supplies  Paper       50   5   0.5   -25   (order O3 is returned)
 5    O4     Cara      South   Office Supplies  Paper      150   3   0.0    60
 6    O5     Cara      South   Technology       Phone       80   1   0.1     8
 7    O5     Cara      South   Technology       Phone       80   1   0.1     8   (same as row 6 except Row ID)

Hand-calculated facts used by the tests
 total sales 760, total profit 111, total quantity 14, 5 orders, 3 customers
 aggregate margin 111/760; mean of row margins 0.45/7 (these differ on purpose)
 Returns block lists O3 twice and O999 (not in Orders) -> 1 returned order of 5
"""
from __future__ import annotations

import csv
import io

import pandas as pd

from src.load_data import ORDERS_COLUMNS, PEOPLE_COLUMNS, RETURNS_COLUMNS


def order_row(row_id, order_id, order_date, ship_date, customer_id="C1", customer_name="Alice",
              segment="Consumer", region="West", state="California", city="Los Angeles",
              postal="90001", product_id="P1", category="Furniture", sub_category="Chairs",
              product_name="Chair", sales=100.0, quantity=1, discount=0.0, profit=10.0,
              ship_mode="Standard Class", country="United States") -> list[str]:
    """One Orders row as a list of strings, in the real column order."""
    values = {
        "Row ID": row_id, "Order ID": order_id, "Order Date": order_date,
        "Ship Date": ship_date, "Ship Mode": ship_mode, "Customer ID": customer_id,
        "Customer Name": customer_name, "Segment": segment, "Country": country,
        "City": city, "State": state, "Postal Code": postal, "Region": region,
        "Product ID": product_id, "Category": category, "Sub-Category": sub_category,
        "Product Name": product_name, "Sales": sales, "Quantity": quantity,
        "Discount": discount, "Profit": profit,
    }
    return ["" if values[c] is None else str(values[c]) for c in ORDERS_COLUMNS]


def synthetic_order_rows() -> list[list[str]]:
    return [
        order_row(1, "O1", "1/5/2020", "1/8/2020", "C1", "Alice", "Consumer", "West", "California",
                  "Los Angeles", "1040", "P1", "Furniture", "Chairs", "Chair, Large", 100, 1, 0.0, 20),
        order_row(2, "O1", "1/5/2020", "1/8/2020", "C1", "Alice", "Consumer", "West", "California",
                  "Los Angeles", "90001", "P2", "Technology", "Phones", "Phone", 200, 2, 0.0, 50),
        order_row(3, "O2", "2/10/2020", "2/12/2020", "C2", "Bob", "Corporate", "East", "New York",
                  "New York City", "", "P1", "Furniture", "Chairs", "Chair, Large", 100, 1, 0.2, -10),
        order_row(4, "O3", "2/20/2020", "2/25/2020", "C2", "Bob", "Corporate", "East", "New York",
                  "New York City", "10001", "P3", "Office Supplies", "Paper", "Paper", 50, 5, 0.5, -25),
        order_row(5, "O4", "3/1/2020", "3/3/2020", "C3", "Cara", "Home Office", "South", "Texas",
                  "Houston", "77001", "P3", "Office Supplies", "Paper", "Paper", 150, 3, 0.0, 60),
        order_row(6, "O5", "3/5/2020", "3/9/2020", "C3", "Cara", "Home Office", "South", "Texas",
                  "Houston", "77001", "P2", "Technology", "Phones", "Phone", 80, 1, 0.1, 8),
        order_row(7, "O5", "3/5/2020", "3/9/2020", "C3", "Cara", "Home Office", "South", "Texas",
                  "Houston", "77001", "P2", "Technology", "Phones", "Phone", 80, 1, 0.1, 8),
    ]


SYNTHETIC_PEOPLE = [["Anna", "West"], ["Ben", "East"]]
SYNTHETIC_RETURNS = [["Yes", "O3"], ["Yes", "O3"], ["Yes", "O999"]]


def build_csv_text(order_rows=None, people=None, returns=None, include_people=True,
                   include_returns=True) -> str:
    """Write the three-block layout used by the real file."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(ORDERS_COLUMNS)
    writer.writerows(synthetic_order_rows() if order_rows is None else order_rows)
    if include_people:
        writer.writerow(PEOPLE_COLUMNS)
        writer.writerows(SYNTHETIC_PEOPLE if people is None else people)
    if include_returns:
        writer.writerow(RETURNS_COLUMNS)
        writer.writerows(SYNTHETIC_RETURNS if returns is None else returns)
    return buffer.getvalue()


def raw_orders_frame(rows: list[list[str]]) -> pd.DataFrame:
    """A raw (all-string) Orders frame, like load_data.read_sections returns."""
    return pd.DataFrame(rows, columns=ORDERS_COLUMNS)
