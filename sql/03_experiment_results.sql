-- Pre-specified primary, secondary, and guardrail metrics by randomized arm.
SELECT
    experiment_group,
    COUNT(*) AS assigned_users,
    AVG(purchase_24h) AS checkout_completion_rate,
    AVG(net_revenue_24h) AS net_revenue_per_assigned_user,
    AVG(order_value) FILTER (WHERE purchase_24h = 1) AS average_order_value,
    AVG(refund_7d) FILTER (WHERE purchase_24h = 1) AS refund_rate_among_buyers,
    AVG(support_contact_7d) AS support_contact_rate,
    AVG(checkout_latency_ms) AS average_latency_ms
FROM experiment_users
GROUP BY 1
ORDER BY 1;

