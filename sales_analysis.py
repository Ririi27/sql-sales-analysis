"""E-commerce sales analysis with SQL (SQLite + Python).
NOTE: the data is SYNTHETIC (generated here with a fixed seed) so the project is fully reproducible.
Skills shown: multi-table JOINs, GROUP BY, CTEs, window functions (RANK, LAG, running totals), RFM-style segmentation.
"""
import random, sqlite3
from datetime import date, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

random.seed(42)
con = sqlite3.connect("sales.db")
con.executescript("""
DROP TABLE IF EXISTS customers; DROP TABLE IF EXISTS products; DROP TABLE IF EXISTS orders; DROP TABLE IF EXISTS order_items;
CREATE TABLE customers(customer_id INTEGER PRIMARY KEY, city TEXT, signup_date TEXT);
CREATE TABLE products(product_id INTEGER PRIMARY KEY, category TEXT, price REAL);
CREATE TABLE orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT);
CREATE TABLE order_items(order_id INTEGER, product_id INTEGER, quantity INTEGER);
""")
cities = ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Dehradun", "Pune"]
cats = {"Electronics": (800, 5000), "Fashion": (300, 2500), "Home": (200, 3000), "Books": (100, 800), "Beauty": (150, 1500)}
con.executemany("INSERT INTO customers VALUES(?,?,?)",
    [(i, random.choice(cities), str(date(2024, 1, 1) + timedelta(days=random.randint(0, 300)))) for i in range(1, 501)])
prods = [(i, c, round(random.uniform(*cats[c]), 2)) for i, c in enumerate([c for c in cats for _ in range(12)], 1)]
con.executemany("INSERT INTO products VALUES(?,?,?)", prods)
oid = 0
for _ in range(4000):
    oid += 1
    d = date(2024, 1, 1) + timedelta(days=random.randint(0, 729))
    con.execute("INSERT INTO orders VALUES(?,?,?)", (oid, random.randint(1, 500), str(d)))
    for p in random.sample(range(1, len(prods) + 1), random.randint(1, 3)):
        con.execute("INSERT INTO order_items VALUES(?,?,?)", (oid, p, random.randint(1, 3)))
con.commit()

Q = {
"revenue_by_category": """
SELECT p.category, ROUND(SUM(oi.quantity*p.price),0) AS revenue, COUNT(DISTINCT o.order_id) AS orders
FROM order_items oi JOIN products p USING(product_id) JOIN orders o USING(order_id)
GROUP BY p.category ORDER BY revenue DESC;""",

"monthly_revenue_growth": """
WITH m AS (
  SELECT strftime('%Y-%m', o.order_date) AS month, SUM(oi.quantity*p.price) AS revenue
  FROM orders o JOIN order_items oi USING(order_id) JOIN products p USING(product_id) GROUP BY month)
SELECT month, ROUND(revenue,0) AS revenue,
       ROUND(100.0*(revenue-LAG(revenue) OVER(ORDER BY month))/LAG(revenue) OVER(ORDER BY month),1) AS mom_growth_pct,
       ROUND(SUM(revenue) OVER(ORDER BY month),0) AS running_total
FROM m ORDER BY month;""",

"top3_products_per_category": """
WITH r AS (
  SELECT p.category, p.product_id, SUM(oi.quantity*p.price) AS revenue,
         RANK() OVER(PARTITION BY p.category ORDER BY SUM(oi.quantity*p.price) DESC) AS rnk
  FROM order_items oi JOIN products p USING(product_id) GROUP BY p.category, p.product_id)
SELECT category, product_id, ROUND(revenue,0) AS revenue, rnk FROM r WHERE rnk<=3 ORDER BY category, rnk;""",

"customer_segments": """
WITH c AS (
  SELECT o.customer_id, COUNT(DISTINCT o.order_id) AS orders, SUM(oi.quantity*p.price) AS spend
  FROM orders o JOIN order_items oi USING(order_id) JOIN products p USING(product_id) GROUP BY o.customer_id),
t AS (SELECT *, NTILE(4) OVER(ORDER BY spend DESC) AS quartile FROM c)
SELECT CASE quartile WHEN 1 THEN 'Top 25%' WHEN 2 THEN 'Upper-mid' WHEN 3 THEN 'Lower-mid' ELSE 'Bottom 25%' END AS segment,
       COUNT(*) AS customers, ROUND(SUM(spend),0) AS revenue,
       ROUND(100.0*SUM(spend)/(SELECT SUM(spend) FROM c),1) AS pct_of_revenue
FROM t GROUP BY quartile ORDER BY quartile;""",

"revenue_by_city": """
SELECT c.city, ROUND(SUM(oi.quantity*p.price),0) AS revenue, COUNT(DISTINCT c.customer_id) AS customers
FROM customers c JOIN orders o USING(customer_id) JOIN order_items oi USING(order_id) JOIN products p USING(product_id)
GROUP BY c.city ORDER BY revenue DESC;""",
}
out = {}
for name, q in Q.items():
    df = pd.read_sql_query(q, con); out[name] = df
    df.to_csv(f"{name}.csv", index=False)
    print(f"\n== {name} ==\n{df.to_string(index=False)}")
open("queries.sql", "w").write("\n\n".join(f"-- {n}\n{q.strip()}" for n, q in Q.items()))

m = out["monthly_revenue_growth"]
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].plot(m["month"], m["revenue"], color="#4A86E8"); ax[0].set_title("Monthly revenue (INR)")
ax[0].set_xticks(m["month"][::3]); ax[0].tick_params(axis="x", rotation=45)
out["revenue_by_category"].plot.bar(x="category", y="revenue", ax=ax[1], color="#4A86E8", legend=False)
ax[1].set_title("Revenue by category (INR)"); ax[1].tick_params(axis="x", rotation=0)
plt.tight_layout(); plt.savefig("sales_overview.png", dpi=150)
