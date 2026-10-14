# Retail Sales Data Analysis & Business Insights

QSkill Data Science Internship, Beginner Task 1. A reproducible Python analysis of the
**Sample Superstore** dataset: data loading and verification, cleaning with documented
decisions, sales / profit / quantity / customer statistics, product, category, regional,
customer and discount analysis, returned orders, 15 charts, and an insights report.

> **Read this first.** Sample Superstore is a **fictional** retailer's sample data. Findings
> describe this dataset, not a real business. The **licence/usage terms of the file have not
> been independently verified**, which is why the raw CSV is not committed to Git.

## Objectives

1. Load the real file correctly (it contains three tables, see below) and verify it by checksum.
2. Clean it with every decision recorded (missing values, duplicates, types, invalid rows).
3. Compute totals, margins, trends and group performance, with clearly defined metrics.
4. Draw charts only from computed tables and write evidence-based insights.
5. Test the important logic and document what was and was not verified.

## Dataset source and provenance

| Item | Detail |
|---|---|
| File used | `superstore.csv` |
| URL | <https://raw.githubusercontent.com/leonism/sample-superstore/master/data/superstore.csv> |
| Hosting repository | `leonism/sample-superstore` on GitHub (a learning project; its README describes the data as taken from the "legendary dataset 'Sample Superstore'" of a fictional e-commerce company) |
| Size / SHA-256 | 2,304,566 bytes / `af443ca30d732c886f7a1d603f9492f98e9a88c268d47cbc146fe758b1f5d65d` |
| Inspected | 2026-10-11 |
| Licence | **Unverified.** The hosting repository has no LICENSE file, and the original publisher's terms were not confirmed. |
| Original origin | Not independently verified. Other public repositories attribute the dataset to a Kaggle listing; that was not confirmed here. |

The pipeline downloads the file on first run and **checks the SHA-256 above**. If the upstream
file changes, the run stops with a clear message instead of silently analysing different data
(`--allow-changed-data` overrides this after you have looked at the change).

**The file is three tables stacked in one CSV:** Orders (header starts with `Row ID`, 21
columns), People (`Person,Region`, 4 rows) and Returns (`Returned,Order ID`, 800 rows). Reading
it with a single `pd.read_csv` would produce 806 junk "orders", so `src/load_data.py` splits the
blocks first.

### Dataset limitations

- Fictional data; unverified licence (above).
- No cost, inventory, marketing, customer age/gender or time-of-day fields. Profit is used as supplied; how it was derived is not documented.
- All rows are in the United States, so no country comparison is possible.
- The Returns block has only an order-level "Yes": no return date, amount or reason.
- Product ID is not a clean key: some Product IDs map to more than one product name (the count is in the cleaning table).
- Orders cover 2015-01-03 to 2018-12-30 only.

## Project structure

```
retail-sales-analysis/
├── README.md
├── requirements.txt
├── pytest.ini
├── .gitignore
├── run_analysis.py        one-command runner
├── src/
│   ├── load_data.py       download, checksum, split Orders/People/Returns
│   ├── clean.py           cleaning + CleaningReport (decision log)
│   ├── analysis.py        all metric calculations
│   ├── report.py          builds the insights report text from computed results
│   └── plots.py           the 15 charts
├── tests/                 pytest suite (synthetic data + real-data regression tests)
├── docs/
│   ├── evaluator_report.md
│   ├── submission_checklist.md
│   └── interview_prep.md
├── data/raw/              downloaded CSV (git-ignored)
├── data/processed/        cleaned row-level data and rejected rows (git-ignored)
└── outputs/
    ├── figures/           15 PNG charts
    ├── tables/            21 files: CSV tables + summary_stats.json
    ├── insights_report.md
    ├── cleaning_report.md
    └── data_provenance.json
```

`src/report.py` is an addition to the suggested layout: it keeps the text generation out of
`analysis.py` so the calculations stay readable.

## Setup and run

Requires Python 3.10+ (developed and checked on 3.13; see "Tests" for exactly what was run).

```bash
cd retail-sales-analysis
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run_analysis.py             # downloads + verifies the data, runs everything
python -m pytest                   # runs the tests
```

Options: `--raw-file PATH` (use a file you downloaded yourself), `--no-download`,
`--refresh-download`, `--allow-changed-data`, `--duplicate-policy flag|drop`,
`--output-dir`, `--processed-dir`. Exit codes: 0 success, 1 some charts failed, 2 data
could not be loaded or cleaned.

**If the download fails** (no internet, blocked network), the error message explains the
fallback: save the file from the URL above to `data/raw/superstore.csv` yourself and run
again. Nothing is fabricated if the file is missing.

## How the code works (short walkthrough)

- **`load_data.py`**: `ensure_raw_data` downloads (only if missing) and verifies the SHA-256.
  `read_sections` walks the file with Python's `csv` reader, recognises each table by its
  header row and returns three DataFrames of *raw strings*, so nothing is converted at this
  stage. Wrong field counts, missing headers and bad encodings raise `DataLoadError` with the
  line number.
- **`clean.py`**: converts types, applies validity rules, handles duplicates and writes every
  decision to a `CleaningReport`. Rows that fail a rule go to a separate *rejected* table
  with the reason instead of vanishing. Raw data is never modified.
- **`analysis.py`**: one `summarize()` function computes the same metrics for any grouping
  (category, region, customer...); other functions add what is specific (growth, discount
  bands, concentration, return rates). `safe_divide` returns NaN instead of crashing on zero.
- **`plots.py`**: each chart function receives a computed table. Blue = profit/amount,
  red = loss. If one chart fails, the error is reported and the others still draw.
- **`report.py`**: builds `insights_report.md` from the results dictionary, keeping *measured
  results*, *interpretation* and *untested ideas* in separate sections.

## Data cleaning decisions

Copied from `outputs/cleaning_report.md`, which the pipeline writes from the data it loaded:

| # | Step | Affected | Decision |
|---|------|---------:|----------|
| 1 | Rows loaded (Orders section only) | 9,994 | People and Returns blocks were split off before this point, so they are not counted as orders. |
| 2 | Trim whitespace, blank text -> missing | 11 | Counted in cells, not rows. Empty strings become NaN so that missing-value checks work. |
| 3 | Harmonise label spelling (case / inner spaces) | 0 | Cells in Ship Mode, Segment, Country, City, State, Region, Category and Sub-Category were mapped to the most common spelling. Product and customer names are left untouched. |
| 4 | Convert Sales/Quantity/Discount/Profit to numbers and dates to datetime | 0 | Values that could not be parsed (counted in cells): {'Sales': 0, 'Quantity': 0, 'Discount': 0, 'Profit': 0, 'Order Date': 0, 'Ship Date': 0}. Dates use the fixed format %m/%d/%Y; anything else becomes missing and is rejected below. |
| 5 | Postal Code kept as text, leading zeros restored | 438 | Codes shorter than 5 digits (e.g. 1040) were left-padded with zeros (01040). Postal Code is an identifier, not a number. |
| 6 | Validity checks (missing key fields, Sales <= 0, bad Quantity, Discount outside 0-1, non-finite Profit, ship before order) | 0 | 21 rules checked. Rows breaking any rule are moved to a separate rejected table with the reason, not silently dropped. Rows failing per rule: none. |
| 7 | Exact duplicate rows (all columns incl. Row ID) | 0 | Identical in every column, so a re-loaded record: the later copy is removed. |
| 8 | Row ID uniqueness check | 0 | Row ID is only a sequence number. Repeats would be reported here but rows are not removed because other fields differ. |
| 9 | Ambiguous duplicates (same except Row ID) | 1 | Identical in every column except Row ID. Row ID differs, and the same product can legitimately appear twice in one order, so there is no proof these are errors: KEPT and flagged in `possible_duplicate`. Their Sales are 281.37 (0.0122% of total), so the conclusion does not depend on this choice. Use --duplicate-policy drop to remove them. |
| 10 | Missing Postal Code (kept as missing) | 11 | Not imputed: inventing a postal code would fabricate data, and no analysis here uses it. City/State for these rows are present. |
| 11 | Product IDs with more than one product name | 32 | Counted in Product IDs. Product ID alone is not a reliable key, so product-level analysis groups by Product ID + Product Name (+ Category/Sub-Category). |
| 12 | Derived columns added | 9,994 | order_year, order_month, order_month_num, ship_days, row_margin (Profit / Sales per line; Sales > 0 is guaranteed by the validity checks), is_loss (Profit < 0), is_returned. |
| 13 | Rows kept for analysis | 9,994 | 9,994 loaded -> 9,994 kept, 0 rejected, 0 removed as duplicates. |
| 14 | Returns rows loaded | 800 | Rows in the Returns block. The same Order ID can appear on several rows. |
| 15 | Returns rows without an Order ID | 0 | Cannot be matched to an order, so they are dropped. |
| 16 | Returns rows whose Returned value is not 'Yes' | 0 | Only 'Yes' is treated as a return; anything else is ignored. |
| 17 | Repeated Order IDs in Returns | 504 | The Returns block repeats order IDs; the return flag is order-level, so each order is counted once (296 unique returned orders). |
| 18 | Returned Order IDs not found in Orders | 0 | Cannot be linked to any sales line (or the order was rejected); they are ignored. |
| 19 | Order lines flagged as belonging to a returned order | 800 | The source has only an order-level flag (no return date, amount or reason), so every line of the order is flagged. |
| 20 | People rows (Person per Region) | 4 | 0 repeated regions dropped (first kept). The file does not say what the Person's role is, so the report only calls them 'person listed for the region'. |
| 21 | People regions not present in Orders | 0 | Counted in regions; such rows are harmless and ignored. |

Why the main decisions were made:

- **Ambiguous duplicate kept, not deleted.** One pair of lines is identical except Row ID.
  Retail orders can legitimately contain the same product twice, so deleting it would be a
  guess. It is flagged (`possible_duplicate`); the cleaning table above states its Sales and their share of the
  total, which is tiny, so no conclusion depends on it. `--duplicate-policy drop` removes it.
- **Missing Postal Code not imputed.** Inventing a code would fabricate data and nothing here uses it.
- **Postal codes restored to 5 characters.** Leading zeros had been lost in the file (e.g. New England codes).
- **Rejected rows are kept apart.** None were rejected in this file; the rules are tested on synthetic bad rows.

## Methodology and metric definitions

| Metric | Definition |
|---|---|
| Sales, Profit, Quantity | sums of the corresponding columns |
| Aggregate profit margin | total profit / total sales for a group; weights each line by its sales. **Used for all comparisons.** |
| Mean row margin | average of Profit / Sales over individual lines; gives a $5 line the same weight as a $5,000 line. Reported for contrast only |
| Average order value | sales / number of distinct Order IDs |
| Loss-making line | a line with negative profit |
| Customer concentration | share of sales from the top 10 customers and from the top 20% of customers |
| Discount band | `0%`, `>0-10%`, `>10-20%`, `>20-30%`, `>30-50%`, `>50%` (right-closed) |
| Spearman correlation | rank correlation of discount vs line margin; chosen because margins are skewed and discount has only 12 distinct values |
| Return rate | returned orders / orders in a group; an order counts in every category it contains |
| Growth | year-over-year change in sales, only between two complete 12-month years |

All results are descriptive. No significance tests, forecasts or causal claims are made.

## Generated outputs

**Charts (`outputs/figures/`)**: 01 yearly sales/profit; 02 monthly trend (line); 03 sales
heatmap year x month; 04 category sales/profit; 05 sub-category profit; 06 region
sales/profit; 07 top/bottom states; 08 segment sales/profit; 09 top customers; 10 customer
concentration curve; 11 discount bands vs margin; 12 discount vs margin scatter; 13 margin heatmap
sub-category x region; 14 best and worst products; 15 return rates.

**Tables (`outputs/tables/`)**: yearly, monthly, seasonality, sales_year_month, category,
subcategory, region, state, segment, customers, lorenz, products, discount_bands,
discount_levels, discount_by_category, margin_subcategory_region, returns_compare,
return_rate_region / segment / category, and `summary_stats.json` (KPIs and other scalar results).

**Reports**: `outputs/insights_report.md`, `outputs/cleaning_report.md`,
`outputs/data_provenance.json`, plus `docs/evaluator_report.md`.

## Findings

Copied from `outputs/insights_report.md` (generated by the code from the data). Sections 1-7 are
measured; section 8 is interpretation; section 9 lists ideas that were **not** tested.

### 1. Measured results: overall

- **Scope.** 5,009 orders (9,994 order lines) from 793 customers between 2015-01-03 and 2018-12-30.
- **Totals.** Sales $2,297,201, profit $286,397, quantity 37,873 units. Aggregate profit margin (total profit / total sales) is 12.5%.
- **Two different margins.** The average of line-level margins is 12.0% (median 27.0%). It differs from the aggregate margin because it gives a small line the same weight as a large one. The aggregate figure is used for all comparisons below.
- **Loss-making lines.** 1,871 of 9,994 order lines (18.7%) have negative profit.

### 2. Measured results: trends

- **By year.** 2015: sales $484,247, profit $49,544 (margin 10.2%); 2016: sales $470,533, profit $61,619 (margin 13.1%); 2017: sales $609,206, profit $81,795 (margin 13.4%); 2018: sales $733,215, profit $93,439 (margin 12.7%).
- **Year-over-year sales growth** (only between complete 12-month years): 2016 -2.8%, 2017 +29.5%, 2018 +20.4%.
- **Seasonality.** Highest average monthly sales by calendar month: November ($88,115), December ($81,323), September ($76,912). Lowest: February ($14,938), January ($23,731), April ($34,441). (Averages over 4 year(s) of data.)

### 3. Measured results: categories and products

- **Categories (ordered by profit).** Technology: sales $836,154 (36.4% of total), profit $145,455, margin 17.4%; Office Supplies: sales $719,047 (31.3% of total), profit $122,491, margin 17.0%; Furniture: sales $742,000 (32.3% of total), profit $18,451, margin 2.5%.
- **Most profitable sub-categories.** Copiers (Technology) $55,618, margin 37.2%; Phones (Technology) $44,516, margin 13.5%; Accessories (Technology) $41,937, margin 25.1%.
- **Loss-making sub-categories (3 of 17).** Tables (Furniture) -$17,725 on sales of $206,966; Bookcases (Furniture) -$3,473 on sales of $114,880; Supplies (Office Supplies) -$1,189 on sales of $46,674.
- **Products** (Product ID + name; 1,894 products). 306 (16.2%) have negative total profit, together losing $77,092; profitable products together earned $363,489. Highest-profit product: Canon imageCLASS 2200 Advanced Copier ($25,200). Largest loss: Cubify CubeX 3D Printer Double Head Print (-$8,880).

### 4. Measured results: regions and states

- **Regions (ordered by profit).** West: sales $725,458, profit $108,418, margin 14.9%; East: sales $678,781, profit $91,523, margin 13.5%; South: sales $391,722, profit $46,749, margin 11.9%; Central: sales $501,240, profit $39,706, margin 7.9%.
- **States.** 10 of 49 states have negative total profit: Texas (-$25,729), Ohio (-$16,971), Pennsylvania (-$15,560), Illinois (-$12,608), North Carolina (-$7,491), Colorado (-$6,528), Tennessee (-$5,342), Arizona (-$3,428), Florida (-$3,399), Oregon (-$1,190). Most profitable: California ($76,381), New York ($74,039), Washington ($33,403).

### 5. Measured results: segments and customers

- **Segments.** Consumer: sales $1,161,401 (50.6%), margin 11.5%, avg order value $449; Corporate: sales $706,146 (30.7%), margin 13.0%, avg order value $466; Home Office: sales $429,653 (18.7%), margin 14.0%, avg order value $473.
- **Customer concentration.** The top 10 customers account for 6.7% of sales; the top 20% of customers (159 of 793) account for 48.1%. The highest-sales customer is Sean Miller ($25,043).
- **Repeat buying.** Median 6 orders per customer; 98.5% of customers ordered at least twice.
- **Loss-making customers.** 155 customers (19.5%) have negative total profit, together -$71,224.

### 6. Measured results: discounts

- **Discount band vs aggregate margin.** 0%: margin 29.5% (4,798 lines, 0% loss-making); >0-10%: margin 16.6% (94 lines, 4% loss-making); >10-20%: margin 11.6% (3,709 lines, 14% loss-making); >20-30%: margin -10.0% (227 lines, 92% loss-making); >30-50%: margin -24.8% (310 lines, 92% loss-making); >50%: margin -119.2% (856 lines, 100% loss-making).
- **Rank correlation.** Spearman correlation between a line's discount and its margin is -0.65 (52.0% of lines carry a discount).
- The lowest discount band with a negative aggregate margin is >20-30%.
- **Category x discount cells with negative margin (at least 30 lines):** Furniture, >20-30%: -10.8% (222 lines); Furniture, >30-50%: -39.2% (167 lines); Furniture, >50%: -108.1% (153 lines); Office Supplies, >50%: -119.3% (680 lines); Technology, >30-50%: -13.3% (143 lines).

### 7. Measured results: returns

- **Returns.** 296 of 5,009 orders (5.9%) are flagged as returned; they hold 7.9% of total sales.
- Returned orders average $610 in sales and 2.7 lines, versus $449 and 2.0 lines for other orders. Their aggregate margin is 12.9% versus 12.4%.
- Return rate by region: West 11.7%, Central 3.3%, East 3.1%, South 2.9%.
- Return rate by segment: Corporate 6.1%, Consumer 6.0%, Home Office 5.4%.
- Return rate by category: Technology 8.0%, Furniture 7.7%, Office Supplies 6.3%.

### 8. Interpretation (readings of the numbers, with caveats)

- The >20-30% discount band is the lowest one with a negative aggregate margin, and higher bands are listed above with their own margins. This is an association: the data has no cost field and discounts were not assigned at random (they may cluster in particular categories or products), so it does not prove that discounts caused the losses.
- The loss-making sub-categories may reflect discounting, product cost, or both. The data cannot separate these because costs are not provided.
- Sales are spread across many customers (top 10 = 6.7%), so within this dataset there is no sign of dependence on a handful of buyers.
- The West region's return rate (11.7%) is 2.0x the overall rate (5.9%); the other regions range from 2.9% to 3.3%. The file has no return reason, so the cause cannot be determined here.
- The return flag is order-level with no date, amount or reason. It is unknown whether returned sales were refunded, so reported sales and profit may include value that was later reversed.

### 9. Ideas to investigate (NOT tested in this project)

- Review discount rules for lines in the >20-30% band and above: compare loss-making lines against a target margin (needs cost data).
- Investigate pricing and discounting for the loss-making sub-categories listed above before changing assortment.
- Compare the biggest loss-making states (Texas, Ohio, Pennsylvania) with profitable states on average discount and sub-category mix; both fields exist in this dataset, so this can be tested next.

### Limits of this analysis

- Fictional data; the licence of the file has not been independently verified.
- No cost, inventory, marketing or customer-demographic fields exist, so margin drivers and customer value beyond sales/profit cannot be explained.
- Margins are computed from the Profit column as supplied; how Profit was derived is not documented in the source.
- Results are descriptive. No significance tests or causal claims were made.

## Tests

```bash
python -m pytest
```

The suite has four layers: loader (splitting, malformed input, checksum, download failure),
cleaning (types, every validity rule, duplicates, label spelling, input not mutated),
analysis (metrics against **hand-calculated** values on a 7-line synthetic dataset, edge
cases such as zero sales and incomplete years), and end-to-end (the CLI on synthetic files,
and charts written as real PNGs). A real-data test class (skipped if the file is absent)
pins the headline numbers and cross-checks them against a plain-pandas calculation that
uses none of the project code.

**Observed results (actually executed):**

- Fresh virtual environment, `pip install -r requirements.txt` (Python 3.13.16, pandas 3.0.6,
  numpy 2.5.4, matplotlib 3.11.2, seaborn 0.13.2, pytest 9.1.1): **115 passed, 5 warnings in 20.57 s**.
  The same environment ran `python run_analysis.py` from a copy with no data and no outputs:
  it downloaded the file, the checksum matched, and exit code was 0.
- Run `pytest` before the first `run_analysis.py` and the 6 real-data tests are skipped (observed: 109 passed, 6 skipped); once the CSV has been downloaded all 115 run.
- The warnings are a seaborn `PendingDeprecationWarning` about `set_bad`; they come from the
  library, not from this project's code.

**Not verified:** other Python versions, pandas 2.x, Windows/macOS, and chart appearance beyond
a visual check of the generated PNGs during development (the tests only check that charts are valid image files).
Fonts differ between machines, so PNGs can differ slightly in pixels; the tables and reports
were byte-identical between two environments.

## Known limitations

- The dataset is fictional, the licence is unverified, and it has no cost data (see above).
- Discount and margin relationships are associations; discounts are not randomly assigned.
- The return flag is order-level with no reason or amount; refunds may not be reflected in Sales/Profit.
- Product-level results use Product ID + name because the ID alone is ambiguous for some products.
- Customer names appear in the top-customer chart and tables; they come from the fictional dataset.
