-- Only the two segments declared before analysis are included.
WITH segments AS (
    SELECT 'device_type' AS segment_name, device_type AS segment_value, * FROM experiment_users
    UNION ALL
    SELECT 'new_vs_returning', new_vs_returning, * FROM experiment_users
)
SELECT
    segment_name, segment_value, experiment_group,
    COUNT(*) AS assigned_users,
    AVG(purchase_24h) AS purchase_rate,
    AVG(net_revenue_24h) AS revenue_per_user
FROM segments
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

