# Interview preparation

Short, honest answers grounded in this project, written in the first person so you can practise them. **Only use an answer once you have re-run the code, checked the numbers yourself and genuinely understand and agree with it.** Change anything that is not true for you.

**1. Why this dataset?**
It is a well-known teaching dataset with sales, profit, quantity, discount, customer, region and product fields, so every analysis in the task is possible. I should say plainly that it is *fictional* and that I could not verify its licence.

**2. What was tricky about the file?**
It is three tables in one CSV (Orders, People, Returns). A normal `read_csv` gives 10,800 rows with 806 almost-empty "orders". The loader recognises each header and splits the file first.

**3. How did you handle duplicates?**
Zero exact duplicates. One pair is identical except Row ID. I kept it and flagged it, because the same product can legitimately appear twice in an order and there is no evidence it is an error. It is a tiny share of sales, so the conclusions do not depend on it, and `--duplicate-policy drop` shows the alternative.

**4. Why not fill the 11 missing postal codes?**
Any value would be invented, and no analysis uses postal code. They are all one city.

**5. Aggregate margin vs the average of row margins?**
Aggregate margin (12.5%) is total profit over total sales, so big lines count more. The mean of row margins (12.0%) treats every line equally. They answer different questions; I used the aggregate for comparisons.

**6. What does the discount analysis show, and what does it not show?**
Margin falls as discounts rise and turns negative from the >20-30% band; Spearman correlation is -0.65. It does not prove discounts *cause* losses: there is no cost data and discounts are not randomly assigned.

**7. Why Spearman and not Pearson?**
Row margins are skewed with extreme values and discount takes only 12 distinct values, so rank-based correlation is more robust.

**8. Which findings would you trust least?**
Anything about returns: the flag is order-level with no reason, date or amount, and we do not know whether sales were refunded. Also product-level results, because Product ID is not a clean key.

**9. How do you know the numbers are right?**
Unit tests compare results with values calculated by hand on a small dataset, and the real-data totals were cross-checked with a separate plain-pandas calculation. That is evidence the code does what I intended, not proof the data is true.

**10. What would you do with more time or data?**
Add cost data to explain margins, test discount effects within category (the cross-tab hints at differences), and look at returns by product and reason if available.

**11. What did you not do?**
No significance tests, forecasting or machine learning (not required), no testing on other Python versions or operating systems.

**12. Which parts of the code can you explain line by line?**
Practise with `src/load_data.py::read_sections`, `src/clean.py::clean_orders` and `src/analysis.py::summarize`. If you cannot explain a part yet, say so and read it before the interview.
