"""Generate a reproducible user-randomized checkout experiment."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260417
START = pd.Timestamp("2025-02-03")
DAYS = 28


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def generate(output_dir: str | Path = "data/raw", n_users: int = 48_000) -> dict[str, int]:
    """Create one row per eligible assigned user plus a daily exposure table.

    Parameters are fixed before analysis. The treatment has a modest device-varying
    checkout effect, lower latency, a small AOV trade-off, and no guaranteed
    improvement in revenue or refund guardrails.
    """
    rng = np.random.default_rng(SEED)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    user_id = np.array([f"E{i:06d}" for i in range(1, n_users + 1)])
    day = rng.integers(0, DAYS, n_users)
    second = rng.integers(9 * 3600, 23 * 3600, n_users)
    assigned_at = START + pd.to_timedelta(day, unit="D") + pd.to_timedelta(second, unit="s")

    country = rng.choice(["UK", "Germany", "France", "Spain", "Netherlands"], n_users,
                         p=[.30, .22, .19, .16, .13])
    channel = rng.choice(["direct", "organic_search", "paid_search", "paid_social", "referral"], n_users,
                         p=[.22, .27, .19, .20, .12])
    returning = rng.random(n_users) < np.where(channel == "direct", .58, np.where(channel == "referral", .48, .34))
    device = np.where(rng.random(n_users) < np.where(channel == "paid_social", .82, .64), "mobile", "desktop")
    latent_intent = rng.normal(0, 1, n_users) + .34 * returning + .12 * (channel == "direct") - .15 * (channel == "paid_social")

    # Randomization is independent of user characteristics and occurs at the first
    # eligible checkout start. A hash-like Bernoulli draw produces natural imbalance.
    treatment = rng.random(n_users) < .5
    group = np.where(treatment, "treatment", "control")

    pre_sessions = np.clip(rng.poisson(np.exp(.62 + .32 * latent_intent)), 0, 18)
    pre_checkout = np.clip(rng.binomial(np.maximum(pre_sessions, 1), sigmoid(-1.15 + .48 * latent_intent)), 0, None)
    pre_purchase = rng.random(n_users) < sigmoid(-1.45 + .78 * latent_intent + .35 * returning)
    pre_revenue = np.where(pre_purchase, rng.lognormal(np.log(78) + .13 * latent_intent, .48), 0)

    country_effect = pd.Series(country).map({"UK": .08, "Germany": .04, "France": 0,
                                              "Spain": -.07, "Netherlands": .05}).to_numpy()
    base_logit = (-.28 + .67 * latent_intent + .22 * returning - .13 * (device == "mobile") +
                  country_effect + .08 * (channel == "direct") - .08 * (channel == "paid_social"))
    # Pre-specified treatment effect: larger on mobile, small on desktop. A mild
    # early novelty component decays during week one but does not reverse.
    treatment_logit = treatment * np.where(device == "mobile", .082, .018)
    novelty = treatment * np.maximum(0, (6 - day) / 6) * .025
    purchase_probability = sigmoid(base_logit + treatment_logit + novelty)
    purchase = rng.random(n_users) < purchase_probability

    order_value = np.zeros(n_users)
    buyer_value = rng.lognormal(np.log(82) + .11 * latent_intent[purchase] + .07 * returning[purchase], .43)
    buyer_value *= np.where(treatment[purchase], .982, 1.0)
    order_value[purchase] = np.round(buyer_value, 2)
    refund_probability = sigmoid(-3.40 + .24 * (device == "mobile") + .13 * treatment + .22 * (order_value > 130))
    refund = purchase & (rng.random(n_users) < refund_probability)
    revenue = np.where(refund, 0, order_value)

    support_probability = sigmoid(-2.75 + .24 * (device == "mobile") - .12 * treatment + .18 * ~returning)
    support_contact = rng.random(n_users) < support_probability
    latency_ms = np.maximum(350, rng.normal(np.where(treatment, 1760, 2180), 410)).round().astype(int)
    post_sessions_7d = np.clip(1 + rng.poisson(np.exp(-.10 + .18 * latent_intent + .18 * ~purchase)), 1, 12)
    checkout_started = np.ones(n_users, dtype=int)  # eligibility trigger

    data = pd.DataFrame({
        "user_id": user_id, "experiment_group": group, "assignment_timestamp": assigned_at,
        "country": country, "device_type": device, "acquisition_channel": channel,
        "new_vs_returning": np.where(returning, "returning", "new"),
        "pre_sessions_28d": pre_sessions, "pre_checkout_starts_28d": pre_checkout,
        "pre_purchase_28d": pre_purchase.astype(int), "pre_revenue_28d": np.round(pre_revenue, 2),
        "sessions_7d": post_sessions_7d, "checkout_started": checkout_started,
        "purchase_24h": purchase.astype(int), "order_value": order_value,
        "net_revenue_24h": np.round(revenue, 2), "refund_7d": refund.astype(int),
        "support_contact_7d": support_contact.astype(int), "checkout_latency_ms": latency_ms,
    }).sort_values("assignment_timestamp")
    data.to_csv(output / "experiment_users.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

    daily = (data.assign(assignment_date=data.assignment_timestamp.dt.date)
             .groupby(["assignment_date", "experiment_group"]).agg(
                 assigned_users=("user_id", "size"), purchases=("purchase_24h", "sum"),
                 revenue=("net_revenue_24h", "sum"), refunds=("refund_7d", "sum"),
                 support_contacts=("support_contact_7d", "sum")).reset_index())
    daily.to_csv(output / "daily_experiment.csv", index=False)
    return {"users": len(data), "days": data.assignment_timestamp.dt.date.nunique()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/raw")
    parser.add_argument("--users", type=int, default=48_000)
    args = parser.parse_args()
    print(generate(args.output_dir, args.users))

