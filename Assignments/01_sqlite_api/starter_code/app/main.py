"""
Assignment 01 -- SQLite behind a FastAPI service.

Run it from the starter folder, either way:
    python -m app.main                   # uses the __main__ block below (port 8001)
    uvicorn app.main:app --port 8001     # equivalent

Then open http://127.0.0.1:8001/docs

(Do NOT run `python app/main.py` -- the package-relative imports need the
`app.` package context, which only `-m app.main` / uvicorn provide.)

Q01 below is a worked example. Add Q02-Q15 the same way, copying the SQL from
../QUERIES.md. Every experiment route takes ?db=<name> (e.g. ?db=noidx_1m).
"""

from __future__ import annotations

import random  # noqa: F401  -- you need this for Q12 /fast
import sqlite3

from fastapi import Depends, FastAPI, HTTPException  # noqa: F401
from fastapi.responses import RedirectResponse

from .auth import require_api_key
from .experiment import get_exp_db, run_query
from .models import NewPurchase  # noqa: F401  -- you need this for Q15

app = FastAPI(title="SQLite API -- Assignment 01")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Bare host -> the Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict:
    return {"ok": True}

# --------------------------------------------------------------------------- #
# Routes
#
# FastAPI matches top to bottom, so keep the fixed paths (/purchases/page,
# /purchases/sample, .../fast) above anything shaped like /purchases/{x}.
# --------------------------------------------------------------------------- #

# Phase 1 ------------------------------------------------------------------- #
Q01_SQL = """
SELECT c.customer_id, c.first_name, c.last_name, c.email, c.zipcode, z.state_code
FROM customers c
JOIN zipcodes z ON z.zipcode = c.zipcode
WHERE c.customer_id = :customer_id
"""

@app.get("/customers/{customer_id}", dependencies=[Depends(require_api_key)])
def q01_customer(
    customer_id: int,
    db: sqlite3.Connection = Depends(get_exp_db)):
    return run_query(db, Q01_SQL, {"customer_id": customer_id})

Q02_SQL = """
SELECT product_id, product_name, unit_price
FROM products
ORDER BY product_id
LIMIT :limit OFFSET :offset
"""
@app.get("/products", dependencies=[Depends(require_api_key)])
def q02_product(
    limit: int,
    offset: int,
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q02_SQL, {"limit": limit, "offset": offset})

Q03_SQL = """
SELECT purchase_id, customer_id, product_id, department, amount, purchase_date
FROM purchases
WHERE purchase_date >= :start AND purchase_date < :end
ORDER BY purchase_date
LIMIT 100
"""

@app.get("/purchases", dependencies=[Depends(require_api_key)])
def q03_purchase(
    start: str,
    end: str,
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q03_SQL, {"start": start, "end": end})

# Phase 2 ------------------------------------------------------------------- #
Q04_SQL = """
SELECT pu.purchase_id, pu.purchase_date, pr.product_name, pu.department, pu.amount
FROM purchases pu
JOIN products pr ON pr.product_id = pu.product_id
WHERE pu.customer_id = :customer_id
ORDER BY pu.purchase_date DESC
LIMIT 100
"""

@app.get("/customers/{customer_id}/purchases", dependencies=[Depends(require_api_key)])
def q04_customer_purchase(
    customer_id: int,
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q04_SQL, {"customer_id": customer_id})

Q05_SQL = """
SELECT COUNT(*) AS num_purchases
FROM purchases
WHERE department = :department
"""

@app.get("/stats/department-count", dependencies=[Depends(require_api_key)])
def q05_department_count(
    department: str,
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q05_SQL, {"department": department})

Q06_SQL = """
WITH days AS (
    SELECT DISTINCT purchase_date AS day
    FROM purchases
    WHERE customer_id = :customer_id
),
islands AS (
    SELECT day,
           julianday(day) - ROW_NUMBER() OVER (ORDER BY day) AS grp
    FROM days
)
SELECT MIN(day) AS streak_start, MAX(day) AS streak_end, COUNT(*) AS days
FROM islands
GROUP BY grp
HAVING COUNT(*) >= 2
ORDER BY days DESC, streak_start
LIMIT 10
"""

@app.get("/customers/{customer_id}/streaks", dependencies=[Depends(require_api_key)])
def q06_customer_streaks(
    customer_id: int,
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q06_SQL, {"customer_id": customer_id})

Q07_SQL = """
WITH spend AS (
    SELECT customer_id, SUM(amount) AS total
    FROM purchases
    WHERE purchase_date >= :start AND purchase_date < :end
    GROUP BY customer_id
)
SELECT customer_id, ROUND(total, 2) AS total,
       RANK() OVER (ORDER BY total DESC) AS rank
FROM spend
ORDER BY total DESC
LIMIT 20
"""

@app.get("/stats/leaderboard", dependencies=[Depends(require_api_key)])
def q07_stats_leaderboard(
    start: str,
    end: str,
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q07_SQL, {"start": start, "end": end})

Q08_SQL = """
SELECT pr.product_id, pr.product_name
FROM products pr
WHERE NOT EXISTS (
    SELECT 1
    FROM purchases pu
    JOIN customers c ON c.customer_id = pu.customer_id
    JOIN zipcodes  z ON z.zipcode     = c.zipcode
    WHERE pu.product_id = pr.product_id
      AND z.state_code  = :state
)
ORDER BY pr.product_id
LIMIT 100
"""

@app.get("/products/dead", dependencies=[Depends(require_api_key)])
def q08_dead_state_products(
    state: str,
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q08_SQL, {"state": state})

Q09_SQL = """
SELECT z.state_code, COUNT(*) AS num_purchases, ROUND(SUM(pu.amount), 2) AS revenue
FROM purchases pu
JOIN customers c ON c.customer_id = pu.customer_id
JOIN zipcodes  z ON z.zipcode     = c.zipcode
GROUP BY z.state_code
ORDER BY revenue DESC
"""

@app.get("/stats/revenue-by-state", dependencies=[Depends(require_api_key)])
def q09_revenue_by_state(
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q09_SQL)

Q10_SQL = """
SELECT pr.product_id, pr.product_name,
       COUNT(*) AS num_purchases, ROUND(SUM(pu.amount), 2) AS revenue
FROM purchases pu
JOIN products pr ON pr.product_id = pu.product_id
GROUP BY pr.product_id
ORDER BY revenue DESC
LIMIT 10
"""

@app.get("/products/top", dependencies=[Depends(require_api_key)])
def q10_top_products(
    db: sqlite3.Connection = Depends(get_exp_db),
):
    return run_query(db, Q10_SQL)

# Phase 3 -- each has a slow route and a /fast route ------------------------ #

# TODO Q11  GET /purchases/page?offset=        GET /purchases/page/fast?after_id=
# TODO Q12  GET /purchases/sample              GET /purchases/sample/fast
# TODO Q13  GET /stats/revenue-by-month        GET /stats/revenue-by-month/fast
# TODO Q14  GET /reports/cube?start=&end=&min_purchases=
#                                              GET /reports/cube/fast?(same)

# Phase 4 ------------------------------------------------------------------- #

# TODO Q15  POST /purchases   (the full code is in QUERIES.md)


# --------------------------------------------------------------------------- #
# Dev entrypoint:  python -m app.main   (run from the starter folder)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app.main:app",   # import string, so --reload can re-import on change
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8001")),
        reload=os.environ.get("RELOAD", "1") == "1",
    )
