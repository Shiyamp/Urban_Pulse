-- URBAN PULSE - 15 analyst tasks (MySQL 8+). Run in MySQL Workbench.
USE urban_pulse_db;

-- 1. Total distinct request volume
SELECT COUNT(DISTINCT unique_key) AS total_requests FROM service_requests;

-- 2. Top 10 complaint categories
SELECT complaint_type, COUNT(*) AS requests
FROM service_requests GROUP BY complaint_type ORDER BY requests DESC LIMIT 10;

-- 3. Agency workload distribution
SELECT agency, COUNT(*) AS requests,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM service_requests GROUP BY agency ORDER BY requests DESC;

-- 4. Request volume by borough
SELECT borough, COUNT(*) AS requests
FROM service_requests GROUP BY borough ORDER BY requests DESC;

-- 5. Monthly request trend
SELECT created_month, COUNT(*) AS requests
FROM service_requests GROUP BY created_month ORDER BY created_month;

-- 6. Demand by weekday and hour
SELECT created_weekday, created_hour, COUNT(*) AS requests
FROM service_requests
GROUP BY created_weekday, created_hour
ORDER BY FIELD(created_weekday,'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'),
         created_hour;

-- 7. Distribution of recorded statuses
SELECT status, COUNT(*) AS requests,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM service_requests GROUP BY status ORDER BY requests DESC;

-- 8. Descriptive statistics for valid resolution durations (hours)
SELECT COUNT(resolution_hours) AS n, MIN(resolution_hours) AS min_h, MAX(resolution_hours) AS max_h,
       ROUND(AVG(resolution_hours), 2) AS mean_h, ROUND(STDDEV_SAMP(resolution_hours), 2) AS std_h
FROM service_requests WHERE resolution_hours IS NOT NULL;

-- 9. Median resolution duration by complaint category (at least 30 valid cases)
WITH ranked AS (
  SELECT complaint_type, resolution_hours,
         ROW_NUMBER() OVER (PARTITION BY complaint_type ORDER BY resolution_hours) AS rn,
         COUNT(*)     OVER (PARTITION BY complaint_type) AS cnt
  FROM service_requests WHERE resolution_hours IS NOT NULL)
SELECT complaint_type, MAX(cnt) AS valid_cases, ROUND(AVG(resolution_hours), 2) AS median_hours
FROM ranked WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2))
GROUP BY complaint_type HAVING valid_cases >= 30 ORDER BY median_hours DESC;

-- 10. Median resolution duration by agency
WITH ranked AS (
  SELECT agency, resolution_hours,
         ROW_NUMBER() OVER (PARTITION BY agency ORDER BY resolution_hours) AS rn,
         COUNT(*)     OVER (PARTITION BY agency) AS cnt
  FROM service_requests WHERE resolution_hours IS NOT NULL)
SELECT agency, MAX(cnt) AS valid_cases, ROUND(AVG(resolution_hours), 2) AS median_hours
FROM ranked WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2))
GROUP BY agency ORDER BY median_hours DESC;

-- 11. IQR-based outlier investigation
WITH r AS (
  SELECT resolution_hours,
         ROW_NUMBER() OVER (ORDER BY resolution_hours) AS rn,
         COUNT(*) OVER () AS cnt
  FROM service_requests WHERE resolution_hours IS NOT NULL),
q AS (
  SELECT MIN(CASE WHEN rn >= cnt * 0.25 THEN resolution_hours END) AS q1,
         MIN(CASE WHEN rn >= cnt * 0.75 THEN resolution_hours END) AS q3
  FROM r)
SELECT q.q1, q.q3, q.q3 - q.q1 AS iqr,
       q.q1 - 1.5 * (q.q3 - q.q1) AS lower_fence,
       q.q3 + 1.5 * (q.q3 - q.q1) AS upper_fence,
       SUM(s.resolution_hours < q.q1 - 1.5 * (q.q3 - q.q1)
        OR s.resolution_hours > q.q3 + 1.5 * (q.q3 - q.q1)) AS outlier_count,
       COUNT(*) AS valid_rows
FROM service_requests s CROSS JOIN q
WHERE s.resolution_hours IS NOT NULL GROUP BY q.q1, q.q3;

-- 12. Skewness (population formula; Python's .skew() differs slightly) + distribution buckets
SELECT m.n, ROUND(m.mean_h, 2) AS mean_h, ROUND(m.sd, 2) AS sd,
       ROUND(SUM(POW(s.resolution_hours - m.mean_h, 3)) / m.n / POW(m.sd, 3), 3) AS skewness
FROM service_requests s
CROSS JOIN (SELECT COUNT(*) AS n, AVG(resolution_hours) AS mean_h, STDDEV_POP(resolution_hours) AS sd
            FROM service_requests WHERE resolution_hours IS NOT NULL) m
WHERE s.resolution_hours IS NOT NULL GROUP BY m.n, m.mean_h, m.sd;

SELECT CASE WHEN resolution_hours <= 24  THEN '1) up to 24h'
            WHEN resolution_hours <= 72  THEN '2) 24-72h'
            WHEN resolution_hours <= 168 THEN '3) 3-7 days'
            ELSE '4) over 7 days' END AS duration_bucket,
       COUNT(*) AS requests
FROM service_requests WHERE resolution_hours IS NOT NULL GROUP BY duration_bucket ORDER BY duration_bucket;

-- 13. Geographic concentration: borough summary + busiest ~1 km grid cells (valid coordinates only)
SELECT borough, COUNT(*) AS requests, SUM(coord_valid) AS with_valid_coords
FROM service_requests GROUP BY borough ORDER BY requests DESC;

SELECT ROUND(latitude, 2) AS lat_cell, ROUND(longitude, 2) AS lon_cell, COUNT(*) AS requests
FROM service_requests WHERE coord_valid = 1
GROUP BY lat_cell, lon_cell ORDER BY requests DESC LIMIT 15;

-- 14. Recorded closure-rate comparison (by borough, then by agency)
SELECT borough, COUNT(*) AS requests, ROUND(100 * AVG(is_closed), 2) AS closure_rate_pct
FROM service_requests GROUP BY borough ORDER BY closure_rate_pct DESC;

SELECT agency, COUNT(*) AS requests, ROUND(100 * AVG(is_closed), 2) AS closure_rate_pct
FROM service_requests GROUP BY agency HAVING requests >= 30 ORDER BY closure_rate_pct DESC;

-- 15. High volume AND long median resolution (volume >= 100, median above the overall median)
WITH ranked AS (
  SELECT complaint_type, resolution_hours,
         ROW_NUMBER() OVER (PARTITION BY complaint_type ORDER BY resolution_hours) AS rn,
         COUNT(*)     OVER (PARTITION BY complaint_type) AS cnt
  FROM service_requests WHERE resolution_hours IS NOT NULL),
med AS (
  SELECT complaint_type, MAX(cnt) AS valid_cases, AVG(resolution_hours) AS median_hours
  FROM ranked WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2)) GROUP BY complaint_type),
overall AS (
  SELECT AVG(resolution_hours) AS overall_median FROM (
    SELECT resolution_hours,
           ROW_NUMBER() OVER (ORDER BY resolution_hours) AS rn,
           COUNT(*) OVER () AS cnt
    FROM service_requests WHERE resolution_hours IS NOT NULL) x
  WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2)))
SELECT m.complaint_type, m.valid_cases, ROUND(m.median_hours, 2) AS median_hours
FROM med m CROSS JOIN overall o
WHERE m.valid_cases >= 100 AND m.median_hours > o.overall_median
ORDER BY m.valid_cases DESC, m.median_hours DESC;
