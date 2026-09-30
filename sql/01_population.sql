-- Analysis population: all randomized users assigned at their first eligible checkout.
SELECT
    user_id, experiment_group, assignment_timestamp, country, device_type,
    acquisition_channel, new_vs_returning, pre_purchase_28d,
    pre_revenue_28d, purchase_24h, order_value, net_revenue_24h,
    refund_7d, support_contact_7d, checkout_latency_ms
FROM experiment_users
WHERE checkout_started = 1
  AND experiment_group IN ('control', 'treatment');

