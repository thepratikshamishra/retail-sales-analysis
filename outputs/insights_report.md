# Insights report - Retail Sales Data Analysis

_Source: Sample Superstore (fictional retailer; licence not independently verified), orders 2015-01-03 to 2018-12-30. All values computed by this project's code._

All numbers below were computed by this project's code from the cleaned data. Sample Superstore is fictional, so these are findings about this dataset, not about a real company.

## 1. Measured results: overall

- **Scope.** 5,009 orders (9,994 order lines) from 793 customers between 2015-01-03 and 2018-12-30.
- **Totals.** Sales $2,297,201, profit $286,397, quantity 37,873 units. Aggregate profit margin (total profit / total sales) is 12.5%.
- **Two different margins.** The average of line-level margins is 12.0% (median 27.0%). It differs from the aggregate margin because it gives a small line the same weight as a large one. The aggregate figure is used for all comparisons below.
- **Loss-making lines.** 1,871 of 9,994 order lines (18.7%) have negative profit.

## 2. Measured results: trends

- **By year.** 2015: sales $484,247, profit $49,544 (margin 10.2%); 2016: sales $470,533, profit $61,619 (margin 13.1%); 2017: sales $609,206, profit $81,795 (margin 13.4%); 2018: sales $733,215, profit $93,439 (margin 12.7%).
- **Year-over-year sales growth** (only between complete 12-month years): 2016 -2.8%, 2017 +29.5%, 2018 +20.4%.
- **Seasonality.** Highest average monthly sales by calendar month: November ($88,115), December ($81,323), September ($76,912). Lowest: February ($14,938), January ($23,731), April ($34,441). (Averages over 4 year(s) of data.)

## 3. Measured results: categories and products

- **Categories (ordered by profit).** Technology: sales $836,154 (36.4% of total), profit $145,455, margin 17.4%; Office Supplies: sales $719,047 (31.3% of total), profit $122,491, margin 17.0%; Furniture: sales $742,000 (32.3% of total), profit $18,451, margin 2.5%.
- **Most profitable sub-categories.** Copiers (Technology) $55,618, margin 37.2%; Phones (Technology) $44,516, margin 13.5%; Accessories (Technology) $41,937, margin 25.1%.
- **Loss-making sub-categories (3 of 17).** Tables (Furniture) -$17,725 on sales of $206,966; Bookcases (Furniture) -$3,473 on sales of $114,880; Supplies (Office Supplies) -$1,189 on sales of $46,674.
- **Products** (Product ID + name; 1,894 products). 306 (16.2%) have negative total profit, together losing $77,092; profitable products together earned $363,489. Highest-profit product: Canon imageCLASS 2200 Advanced Copier ($25,200). Largest loss: Cubify CubeX 3D Printer Double Head Print (-$8,880).

## 4. Measured results: regions and states

- **Regions (ordered by profit).** West: sales $725,458, profit $108,418, margin 14.9%; East: sales $678,781, profit $91,523, margin 13.5%; South: sales $391,722, profit $46,749, margin 11.9%; Central: sales $501,240, profit $39,706, margin 7.9%.
- **States.** 10 of 49 states have negative total profit: Texas (-$25,729), Ohio (-$16,971), Pennsylvania (-$15,560), Illinois (-$12,608), North Carolina (-$7,491), Colorado (-$6,528), Tennessee (-$5,342), Arizona (-$3,428), Florida (-$3,399), Oregon (-$1,190). Most profitable: California ($76,381), New York ($74,039), Washington ($33,403).

## 5. Measured results: segments and customers

- **Segments.** Consumer: sales $1,161,401 (50.6%), margin 11.5%, avg order value $449; Corporate: sales $706,146 (30.7%), margin 13.0%, avg order value $466; Home Office: sales $429,653 (18.7%), margin 14.0%, avg order value $473.
- **Customer concentration.** The top 10 customers account for 6.7% of sales; the top 20% of customers (159 of 793) account for 48.1%. The highest-sales customer is Sean Miller ($25,043).
- **Repeat buying.** Median 6 orders per customer; 98.5% of customers ordered at least twice.
- **Loss-making customers.** 155 customers (19.5%) have negative total profit, together -$71,224.

## 6. Measured results: discounts

- **Discount band vs aggregate margin.** 0%: margin 29.5% (4,798 lines, 0% loss-making); >0-10%: margin 16.6% (94 lines, 4% loss-making); >10-20%: margin 11.6% (3,709 lines, 14% loss-making); >20-30%: margin -10.0% (227 lines, 92% loss-making); >30-50%: margin -24.8% (310 lines, 92% loss-making); >50%: margin -119.2% (856 lines, 100% loss-making).
- **Rank correlation.** Spearman correlation between a line's discount and its margin is -0.65 (52.0% of lines carry a discount).
- The lowest discount band with a negative aggregate margin is >20-30%.
- **Category x discount cells with negative margin (at least 30 lines):** Furniture, >20-30%: -10.8% (222 lines); Furniture, >30-50%: -39.2% (167 lines); Furniture, >50%: -108.1% (153 lines); Office Supplies, >50%: -119.3% (680 lines); Technology, >30-50%: -13.3% (143 lines).

## 7. Measured results: returns

- **Returns.** 296 of 5,009 orders (5.9%) are flagged as returned; they hold 7.9% of total sales.
- Returned orders average $610 in sales and 2.7 lines, versus $449 and 2.0 lines for other orders. Their aggregate margin is 12.9% versus 12.4%.
- Return rate by region: West 11.7%, Central 3.3%, East 3.1%, South 2.9%.
- Return rate by segment: Corporate 6.1%, Consumer 6.0%, Home Office 5.4%.
- Return rate by category: Technology 8.0%, Furniture 7.7%, Office Supplies 6.3%.

## 8. Interpretation (readings of the numbers, with caveats)

- The >20-30% discount band is the lowest one with a negative aggregate margin, and higher bands are listed above with their own margins. This is an association: the data has no cost field and discounts were not assigned at random (they may cluster in particular categories or products), so it does not prove that discounts caused the losses.
- The loss-making sub-categories may reflect discounting, product cost, or both. The data cannot separate these because costs are not provided.
- Sales are spread across many customers (top 10 = 6.7%), so within this dataset there is no sign of dependence on a handful of buyers.
- The West region's return rate (11.7%) is 2.0x the overall rate (5.9%); the other regions range from 2.9% to 3.3%. The file has no return reason, so the cause cannot be determined here.
- The return flag is order-level with no date, amount or reason. It is unknown whether returned sales were refunded, so reported sales and profit may include value that was later reversed.

## 9. Ideas to investigate (NOT tested in this project)

- Review discount rules for lines in the >20-30% band and above: compare loss-making lines against a target margin (needs cost data).
- Investigate pricing and discounting for the loss-making sub-categories listed above before changing assortment.
- Compare the biggest loss-making states (Texas, Ohio, Pennsylvania) with profitable states on average discount and sub-category mix; both fields exist in this dataset, so this can be tested next.

## Limits of this analysis

- Fictional data; the licence of the file has not been independently verified.
- No cost, inventory, marketing or customer-demographic fields exist, so margin drivers and customer value beyond sales/profit cannot be explained.
- Margins are computed from the Profit column as supplied; how Profit was derived is not documented in the source.
- Results are descriptive. No significance tests or causal claims were made.
