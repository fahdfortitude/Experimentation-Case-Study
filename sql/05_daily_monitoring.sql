-- Daily monitoring supports stability checks; it is not a sequential stopping rule.
SELECT
    CAST(assignment_timestamp AS DATE) AS assignment_date,
    experiment_group,
    COUNT(*) AS assigned_users,
    AVG(purchase_24h) AS purchase_rate,
    AVG(net_revenue_24h) AS revenue_per_user,
    AVG(checkout_latency_ms) AS average_latency_ms,
    SUM(COUNT(*)) OVER (PARTITION BY experiment_group ORDER BY assignment_date) AS cumulative_users
FROM experiment_users
GROUP BY 1, 2
ORDER BY 1, 2;

