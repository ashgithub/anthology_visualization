-- 1. Show me all substations and their capacity in descending order
--sql
SELECT name, capacity_mva
FROM substations
ORDER BY capacity_mva DESC FETCH FIRST 50 ROWS ONLY

-- pgsql 
SELECT substation_name, capacity_mva
FROM GRAPH_TABLE(
  outage_network
  MATCH (s IS substation)
  COLUMNS (
    s.name AS substation_name,
    s.capacity_mva AS capacity_mva
  )
)
ORDER BY capacity_mva DESC FETCH FIRST 50 ROWS ONLY


-- 2. Find circuits with the highest number of customers served
-- sql 
SELECT c.circuit_name,
       c.circuit_code,
       s.name AS substation_name,
       COUNT(cu.id) AS customer_count
FROM circuits c
JOIN substations s
  ON s.id = c.substation_id
LEFT JOIN customers cu
  ON cu.circuit_id = c.id
GROUP BY c.circuit_name, c.circuit_code, s.name
ORDER BY customer_count DESC, c.circuit_name FETCH FIRST 50 ROWS ONLY

-- pqsql 
SELECT circuit_name, customer_count
FROM (
  SELECT gt.circuit_name, COUNT(*) AS customer_count
  FROM GRAPH_TABLE(
    outage_network
    MATCH (ci IS circuit)-[SERVED_BY]->(cu IS customer)
    COLUMNS (
      ci.circuit_name AS circuit_name,
      cu.account_number AS account_number
    )
  ) gt
  GROUP BY gt.circuit_name
  ORDER BY customer_count DESC
)
FETCH FIRST 10 ROWS ONLYo

-- 3. List assets that are currently in overwatch condition (condition_score < 4)
-- sql 
SELECT a.asset_id, a.asset_type, a.condition_score, a.health_index, a.last_maintenance_date, c.circuit_name, s.name AS substation_name
FROM assets a
LEFT JOIN circuits c ON c.id = a.circuit_id
LEFT JOIN substations s ON s.id = a.substation_id
WHERE a.condition_score < 4
ORDER BY a.condition_score ASC, a.asset_id FETCH FIRST 50 ROWS ONLY

-- pgsql 
SELECT asset_id, asset_type, condition_score, health_index, status, criticality
FROM GRAPH_TABLE(
  outage_network
  MATCH (a IS asset)
    WHERE a.condition_score < 4
  COLUMNS (
    a.asset_id AS asset_id,
    a.asset_type AS asset_type,
    a.condition_score AS condition_score,
    a.health_index AS health_index,
    a.status AS status,
    a.criticality AS criticality
  )
) FETCH FIRST 50 ROWS ONLY
/
--   4. What are the most common outage cause categories in the last 6 months?

-- sql
SELECT cause_category, COUNT(*) AS outage_count
FROM outages
WHERE start_time >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY cause_category
ORDER BY outage_count DESC, cause_category FETCH FIRST 50 ROWS ONLY
/

-- pgsql
SELECT cause_category, count(*) as outage_count
FROM GRAPH_TABLE(
  outage_network
  MATCH (o IS outage)
  WHERE o.start_time >= ADD_MONTHS(SYSDATE, -6)
  COLUMNS (
    o.cause_category AS cause_category
  )
)
GROUP BY cause_category
ORDER BY outage_count DESC, cause_category

/

-- 5. Which work orders are still open and their associated asset types?

--sql
SELECT wo.id AS work_order_id, wo.status, a.asset_type
FROM work_orders wo
JOIN assets a ON a.id = wo.asset_id
WHERE wo.completed_time IS NULL
  AND UPPER(wo.status) <> 'COMPLETED'
ORDER BY wo.created_time DESC FETCH FIRST 50 ROWS ONLY

--pgsql
SELECT DISTINCT work_order_id, work_order_status, asset_type
FROM GRAPH_TABLE(
  outage_network
  MATCH (wo IS work_order)-[SERVICES]->(a IS asset)
  WHERE wo.status = 'Open'
  COLUMNS (
    wo.id AS work_order_id,
    wo.status AS work_order_status,
    a.asset_type AS asset_type
  )
)
ORDER BY work_order_id, asset_type FETCH FIRST 50 ROWS ONLY

