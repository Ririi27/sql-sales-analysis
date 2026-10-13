-- revenue_by_category
SELECT p.category, ROUND(SUM(oi.quantity*p.price),0) AS revenue, COUNT(DISTINCT o.order_id) AS orders
FROM order_items oi JOIN products p USING(product_id) JOIN orders o USING(order_id)
GROUP BY p.category ORDER BY revenue DESC;

-- monthly_revenue_growth
WITH m AS (
  SELECT strftime('%Y-%m', o.order_date) AS month, SUM(oi.quantity*p.price) AS revenue
  FROM orders o JOIN order_items oi USING(order_id) JOIN products p USING(product_id) GROUP BY month)
SELECT month, ROUND(revenue,0) AS revenue,
       ROUND(100.0*(revenue-LAG(revenue) OVER(ORDER BY month))/LAG(revenue) OVER(ORDER BY month),1) AS mom_growth_pct,
       ROUND(SUM(revenue) OVER(ORDER BY month),0) AS running_total
FROM m ORDER BY month;

-- top3_products_per_category
WITH r AS (
  SELECT p.category, p.product_id, SUM(oi.quantity*p.price) AS revenue,
         RANK() OVER(PARTITION BY p.category ORDER BY SUM(oi.quantity*p.price) DESC) AS rnk
  FROM order_items oi JOIN products p USING(product_id) GROUP BY p.category, p.product_id)
SELECT category, product_id, ROUND(revenue,0) AS revenue, rnk FROM r WHERE rnk<=3 ORDER BY category, rnk;

-- customer_segments
WITH c AS (
  SELECT o.customer_id, COUNT(DISTINCT o.order_id) AS orders, SUM(oi.quantity*p.price) AS spend
  FROM orders o JOIN order_items oi USING(order_id) JOIN products p USING(product_id) GROUP BY o.customer_id),
t AS (SELECT *, NTILE(4) OVER(ORDER BY spend DESC) AS quartile FROM c)
SELECT CASE quartile WHEN 1 THEN 'Top 25%' WHEN 2 THEN 'Upper-mid' WHEN 3 THEN 'Lower-mid' ELSE 'Bottom 25%' END AS segment,
       COUNT(*) AS customers, ROUND(SUM(spend),0) AS revenue,
       ROUND(100.0*SUM(spend)/(SELECT SUM(spend) FROM c),1) AS pct_of_revenue
FROM t GROUP BY quartile ORDER BY quartile;

-- revenue_by_city
SELECT c.city, ROUND(SUM(oi.quantity*p.price),0) AS revenue, COUNT(DISTINCT c.customer_id) AS customers
FROM customers c JOIN orders o USING(customer_id) JOIN order_items oi USING(order_id) JOIN products p USING(product_id)
GROUP BY c.city ORDER BY revenue DESC;