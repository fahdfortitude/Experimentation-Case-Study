-- Missingness by arm catches asymmetric instrumentation failures.
SELECT
    experiment_group,
    COUNT(*) AS users,
    COUNT_IF(assignment_timestamp IS NULL) / COUNT(*)::DOUBLE AS assignment_timestamp_missing,
    COUNT_IF(device_type IS NULL) / COUNT(*)::DOUBLE AS device_missing,
    COUNT_IF(purchase_24h IS NULL) / COUNT(*)::DOUBLE AS primary_metric_missing,
    COUNT_IF(pre_purchase_28d IS NULL) / COUNT(*)::DOUBLE AS cuped_covariate_missing,
    COUNT_IF(checkout_latency_ms IS NULL) / COUNT(*)::DOUBLE AS latency_missing
FROM experiment_users
GROUP BY 1;

