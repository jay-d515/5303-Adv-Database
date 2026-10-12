# FINDINGS — Assignment 01

## Environment

- SQLite version (`sqlite3 --version`): sqlite3 3.53.2
- Python version (`python --version`): Python 3.14.2
- Machine (CPU, RAM, SSD or spinning disk): 2 CPU cores and 8 GB of RAM
- Row counts (copy from the `make_dbs.py` output):

| Size | purchases | customers | products |
| :--- | --------: | --------: | -------: |
| 10k  |  10,000   |    500    |   100    |
| 100k |  100,000  |   5,000   |   500    |
| 1m   | 1,000,000 |   50,000  |   5,000  |

- Indexes in `idx_1m.db` (paste the output of `sqlite3 data/idx_1m.db ".indexes"`):
 idx_cards_customer, idx_purchases_customer, idx_purchases_department, idx_zipcodes_state, 
idx_customers_zipcode, idx_purchases_date, idx_purchases_prod_amount, 
idx_purchases_cust_amount, idx_purchases_date_cust_amount, idx_purchases_product

```
```

## Results

Paste your whole `results.md` here. All times are median milliseconds.

| Query | noidx_10k | idx_10k | noidx_100k | idx_100k | noidx_1m | idx_1m |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q01 | 0.06 | 0.07 | 0.06 | 0.06 | 0.06 | 0.06 |
| Q02 | 0.06 | 0.11 | 0.11 | 0.10 | 0.08 | 0.10 |
| Q03 | 1.27 | 0.55 | 26.27 | 0.58 | 109.12 | 1.34 |
| Q04 | 1.14 | 1.50 | 30.95 | 14.77 | 86.14 | 53.96 |
| Q05 | 1.21 | 0.06 | 19.29 | 0.29 | 85.53 | 3.58 |
| Q06 | 5.12 | 2.20 | 23.22 | 13.51 | 80.08 | 64.77 |
| Q07 | 2.69 | 1.73 | 29.52 | 8.56 | 185.16 | 114.06 |
| Q08 | 16.38 | 6.01 | 157.05 | 22.76 | 5019.43 | 44.62 |
| Q09 | 11.20 | 4.15 | 133.51 | 24.43 | 2517.63 | 333.41 |
| Q10 | 8.59 | 2.30 | 71.75 | 16.05 | 932.77 | 138.93 |
| Q11 | 0.67 | 0.57 | 7.18 | 3.31 | 31.95 | 34.75 |
| Q11-fast | 0.14 | 0.14 | 0.14 | 0.13 | 0.14 | 0.13 |
| Q12 | 3.90 | 3.46 | 23.80 | 12.73 | 130.09 | 129.98 |
| Q12-fast | 0.10 | 0.10 | 0.11 | 0.10 | 0.13 | 0.15 |
| Q13 | 7.74 | 7.43 | 67.72 | 45.82 | 763.62 | 606.57 |
| Q13-fast | 2.83 | 4.78 | 10.27 | 9.99 | 10.47 | 15.77 |
| Q14 | 10.50 | 16.17 | 83.06 | 152.57 | 1441.48 | 2499.56 |
| Q14-fast | 0.83 | 0.87 | 3.63 | 2.20 | 8.08 | 8.09 |
---

## Phase 1 — Simple reads (Q01–Q03)

| Query | Plan summary in `noidx_1m` | Plan summary in `idx_1m` |
| :---- | :------------------------- | :----------------------- |
| Q01   | SEARCH PRIMARY KEY (rowid=?) + SEARCH sqlite_autoindex_zipcodes_1 (zipcode=?) | SEARCH c PRIMARY KEY (rowid=?) + SEARCH z sqlite_autoindex_zipcodes_1 (zipcode=?) |
| Q03   | SCAN purchases + USE TEMP B-TREE FOR ORDER BY | SEARCH idx_purchases_date |

*A plan summary is the one or two `SCAN` / `SEARCH` lines that matter, e.g. `SCAN purchases + TEMP B-TREE FOR ORDER BY`.*

1. Why is Q01 fast even in `noidx_*`?
- Q01 is fast in both noidx_* and idx_* because they jump straight to a row by its id and jump through a index to just its matching rows. These are two of the fastest plans that can be used in a plan summary.

2. What does SQLite do differently for Q03 in the two databases?
- In noidx_1m, Q03 read every row of the purchases table and built a temporary sorted structure, while in idx_1m, it simply jumped through an index to its matching rows.

## Phase 2 — Where indexes matter (Q04–Q10)

| Query | `noidx_1m` ms | `idx_1m` ms | Speedup (noidx ÷ idx) |
| :---- | ------------: | ----------: | --------------------: |
| Q04   | 86.14 | 53.96 | 1.6x |
| Q05   | 85.53 | 3.58 | 24x |
| Q06   | 80.08 | 64.77 | 1.24x |
| Q07   | 185.16 | 114.06 | 1.62x |
| Q08   | 5019.43 | 44.62 | 112x |
| Q09   | 2517.63 | 333.41 | 7.55x |
| Q10   | 932.77 | 138.93 | 6.71x |

1. Which query had the largest speedup? Quote its two plan summaries and explain the difference.
- Q08 had the largest speedup. noidx_1m was 5019.43 ms and idx_1m was 44.621 ms, about 112x faster. noidx_1m had a plan summary of:
```
- SCAN pr | CORRELATED SCALAR SUBQUERY 1 | SEARCH z USING AUTOMATIC PARTIAL COVERING INDEX (state_code=?) | BLOOM FILTER ON pu (product_id=?) | SEARCH pu USING AUTOMATIC COVERING INDEX (product_id=?) | SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
```
and idx_1m had a plan summary of:
```
- SCAN pr | CORRELATED SCALAR SUBQUERY 1 | SEARCH pu USING INDEX idx_purchases_product (product_id=?) | SEARCH c USING INTEGER PRIMARY KEY (rowid=?) | SEARCH z USING INDEX sqlite_autoindex_zipcodes_1 (zipcode=?)
```
- noidx_1m is slower because it builds temporary indexes and a bloom filter while scanning pr and checking purchases, which are usually slower processes. idx_1m was faster because it used the real idx_purchases_product and zipcode indexes, which allowed it to avoid the extra temporary-index work.

2. Q09 reads every purchase in both databases. Which word in its `idx_1m` plan explains why it's still faster?
- the keyword is "COVERING". explains why its still faster because SQLite can answer them from the index itself instead of reading the full purchase table repeatedly.

3. Why did Q07 only get about 2× faster?
- Q07 only got about 2x faster because the query still has to group and sort a lot of rows, even with a better index. The aggregation cost still dominates  because the idx_1m plan still shows "USE TEMP B-TREE FOR GROUP BY" and "USE TEMP B-TREE FOR ORDER BY".

## Phase 3 — When an index can't save you (Q11–Q14)

| Query                          | slow, `noidx_1m` | slow, `idx_1m` | `/fast`, `idx_1m` |
| :----------------------------- | ---------------: | -------------: | ----------------: |
| Q11 offset → keyset            | 31.95 | 34.75 | 0.13 |
| Q12 random sort → random ids   | 130.09 | 129.09 | 0.15 |
| Q13 revenue by month → summary | 763.62 | 606.57 | 15.77 |
| Q14 cube → summary             | 1441.48 | 2499.56 | 8.09 |

For each, write one or two sentences: **why the slow version is slow** (point at the plan) and **what the rewrite gives up**.

- **Q11:**
```
Slow version: SCAN purchases, so it scans the whole table to skip rows by offset.
Fast version: SEARCH purchases USING INTEGER PRIMARY KEY (rowid>?) uses keyset pagination, so it jumps to the next row instead of scanning everything.
Tradeoff: it gives up simple offset-based pagination.
```
- **Q12:**
```
Slow version: SCAN purchases | USE TEMP B-TREE FOR ORDER BY sorts the whole table.
Fast version: SEARCH purchases USING INTEGER PRIMARY KEY (rowid=?) finds rows directly by id.
Tradeoff: it only works when rowids are the natural ordering.
```
- **Q13:**
```
Slow version: SCAN purchases | USE TEMP B-TREE FOR GROUP BY recomputes the monthly totals from raw rows.
Fast version: SCAN monthly_sales uses the precomputed summary table.
Tradeoff: it is faster but less fresh and less exact than recomputing live.
```
- **Q14:** (also: why is the slow version slower in `idx_1m` than in `noidx_1m`?)
```
Slow version: it computes a cube from raw data and does date/index lookups, so it is expensive even with an index.
Fast version: it reads monthly_sales directly.
Tradeoff: it answers only the precomputed summary, not arbitrary full cube queries.
Why slower in idx_1m than noidx_1m: the indexed date lookup adds extra index probes before the cube work, so the index helps less than expected.
```

## Phase 4 — Write concurrency (Q15)

| Run  | busy_timeout | workers |    n | succeeded (201) | failed (503) | seconds | writes/sec |
| :--- | -----------: | ------: | ---: | --------------: | -----------: | ------: | ---------: |
| A    |            0 |       1 |  200 | 50 | 150 | 1.78 | 28.1 |
| A    |            0 |       1 |  500 | 92 | 408 | 9.79 | 9.4 |
| B    |         5000 |       1 |  200 | 200 | 0 | 2.43 | 82.3 |
| B    |         5000 |       1 |  500 | 500 | 0 | 11.01 | 45.4 |
| C    |            0 |       4 |  200 | 43 | 157 | 1.72 | 25 |
| C    |            0 |       4 |  500 | 108 | 392 | 10.27 | 10.5 |
| D    |         5000 |       4 |  200 | 200 | 0 | 2.00 | 100 |
| D    |         5000 |       4 |  500 | 500 | 0 | 10.49 | 47.7 |

Exact error text from a failed request:

```
from the running the loadtest.py command:
--- 503 ---
{"detail":"database error: database is locked"}
from each request where the database was locked:
503 Service Unavailable
```

Summary-table check (`COUNT(*) FROM purchases` vs. `SUM(num_purchases) FROM monthly_sales`):

| COUNT(*) FROM purchases | SUM(num_purchases) = FROM monthly_sales |
| ----------------------: | --------------------------------------: |
| 101893 | 100000 |


1. What does `busy_timeout` do, and why did B succeed where A failed?
- busy_timeout tells SQLite to wait for a lock before failing. Run B succeeded because the writer paused for 5 seconds and let the lock clear, while A failed immediately with 503s.

3. Did 4 worker processes make SQLite write faster? Why or why not?
- Four workers did not make SQLite faster; they increased lock contention. SQLite still serializes writes, so D only wins because it waits, not because it actually parallelizes writes.

5. Why don't the two summary-check numbers match? What does that cost the `/fast` routes from Phase 3?
- The summary check differs because monthly_sales is a cached aggregate and can drift from the raw purchases table. That is the trade-off for the /fast routes: they are much faster, but they are not exact live data.

## Phase 5 — Conclusions

For each scenario: **SQLite yes or no**, 1–2 sentences, and one number from your results.

1. Internal read-only dashboard, ~10 analysts: Yes, SQLite is fine for light read-heavy analytics with indexes.
2. Mobile app offline local storage: Yes, SQLite is built for local, small-to-medium databases with indexed reads and writes.
3. Thousands of events per second from many servers: No, SQLite is not good for high-write concurrency across many clients because locking and serialization bottleneck it.
4. Fresh throwaway database per automated test: Yes, It is ideal for quick, disposable databases; Q01 was extremely fast at 0.059 ms.
