-- Arm sizes and pre-treatment balance inputs. Outcome columns are deliberately absent.
SELECT
    experiment_group,
    COUNT(*) AS assigned_users,
    AVG((device_type = 'mobile')::INT) AS mobile_share,
    AVG((new_vs_returning = 'returning')::INT) AS returning_share,
    AVG(pre_purchase_28d) AS pre_purchase_rate,
    AVG(pre_revenue_28d) AS mean_pre_revenue,
    AVG(pre_sessions_28d) AS mean_pre_sessions,
    COUNT_IF(user_id IS NULL OR assignment_timestamp IS NULL OR experiment_group IS NULL) AS missing_required
FROM experiment_users
GROUP BY 1
ORDER BY 1;

