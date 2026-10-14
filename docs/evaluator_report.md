# Evaluator report: Retail Sales Data Analysis & Business Insights

**Task:** QSkill Data Science Internship, Beginner Task 1.  
**Data:** Sample Superstore (fictional US retailer), 9,994 order lines, 5,009 orders, 793 customers, 2015-01-03 to 2018-12-30. Source and checksum are in the README; the licence is unverified.  
**Tools:** Python, Pandas, NumPy, Matplotlib, Seaborn (heatmaps), pytest.  
**Run:** `python run_analysis.py` (about 8 seconds). **Test:** `python -m pytest` (115 tests passed in the observed run).

## What was done

1. Downloaded the CSV and verified its SHA-256. The file holds three stacked tables (Orders, People, Returns), which were split before analysis rather than read as one table.
2. Cleaned the Orders table: types, 21 validity rules, duplicates, label spelling, postal codes. Every decision is logged in `outputs/cleaning_report.md`. No rows were rejected for this file; one pair of identical lines (differing only in Row ID) was flagged and kept; 11 missing postal codes were left missing.
3. Computed sales, profit, quantity and margins (aggregate margin, not the average of row margins) overall and by year, month, category, sub-category, region, state, segment, customer, product, discount band and return status.
4. Drew 15 charts from the computed tables and generated the insights report from the results.

## Headline results (computed)

- Sales $2,297,201, profit $286,397, quantity 37,873; aggregate margin 12.5% (mean of row margins 12.0%, a different measure).
- Yearly sales: 2015 $484,247, 2016 $470,533, 2017 $609,206, 2018 $733,215. Profit margin by year: 2015 10.2%, 2016 13.1%, 2017 13.4%, 2018 12.7%.
- **Category:** Technology margin 17.4%, Furniture only 2.5% on sales of $742,000. 3 sub-categories lose money: Tables (-$17,725), Bookcases (-$3,473), Supplies (-$1,189).
- **Region:** West has the best margin (14.9%); Central the worst (7.9%). 10 of 49 states have negative total profit.
- **Discounts:** aggregate margin is 29.5% with no discount, 11.6% at >10-20%, and negative from the >20-30% band (-10.0%); Spearman correlation of discount vs line margin -0.65.
- **Customers:** the top 10 customers give 6.7% of sales; the top 20% give 48.1%. 155 customers (19.5%) have negative total profit.
- **Returns:** 296 of 5,009 orders (5.9%); West region 11.7% versus 2.9% to 3.3% elsewhere. No return reason exists in the data.

## Interpretation and caveats

Discounts in the >20-30% band and above coincide with losses, and Furniture has the lowest category margin (2.5%), but the data has **no cost field** and discounts are not randomly assigned, so these are associations, not proof of cause. Suggestions in the insights report are labelled as untested.

## What was verified

- Unit tests compare metrics with hand-calculated values; real-data totals were cross-checked with an independent plain-pandas calculation.
- Charts were opened and inspected visually; layout defects found during this review were fixed.
- Setup was repeated in a clean virtual environment from `requirements.txt`.

**Not verified:** other Python/pandas versions and operating systems. See README, "Tests" and "Known limitations".
