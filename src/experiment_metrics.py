"""Metric contract for the checkout experiment."""
PRIMARY_METRIC = "purchase_24h"
SECONDARY_METRICS = ["net_revenue_24h", "sessions_7d"]
GUARDRAIL_METRICS = ["order_value", "refund_7d", "support_contact_7d", "checkout_latency_ms"]
PRESPECIFIED_SEGMENTS = ["device_type", "new_vs_returning"]

