"""Analyze experiment health, effects, precision, segments, and time dynamics."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from scipy.stats import norm

from src.statistics import cuped_adjust, mean_effect, proportion_effect, required_sample_size, srm_test

ROOT = Path(__file__).resolve().parents[1]
RAW, PROCESSED, FIGURES = ROOT / "data/raw", ROOT / "data/processed", ROOT / "outputs/figures"
ALPHA, POWER = .05, .80
PLANNING_BASELINE, PLANNING_MDE = .45, .015
BUSINESS_HURDLE = .0075


def standardized_difference(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return (b.mean() - a.mean()) / pooled if pooled else 0.0


def run():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update({"figure.dpi": 130, "savefig.bbox": "tight", "axes.titleweight": "bold"})
    df = pd.read_csv(RAW / "experiment_users.csv", parse_dates=["assignment_timestamp"])
    df["treatment"] = df.experiment_group.eq("treatment").astype(int)
    df["assignment_date"] = df.assignment_timestamp.dt.normalize()
    df["experiment_day"] = (df.assignment_date - df.assignment_date.min()).dt.days + 1

    control, treatment = df[df.treatment.eq(0)], df[df.treatment.eq(1)]
    planned = required_sample_size(PLANNING_BASELINE, PLANNING_MDE, ALPHA, POWER)
    srm = srm_test(len(control), len(treatment))

    balance_rows = []
    balance_variables = {
        "Mobile share": df.device_type.eq("mobile").astype(int),
        "Returning-user share": df.new_vs_returning.eq("returning").astype(int),
        "Pre-period purchase": df.pre_purchase_28d,
        "Pre-period sessions": df.pre_sessions_28d,
        "Pre-period revenue": df.pre_revenue_28d,
    }
    for name, values in balance_variables.items():
        balance_rows.append({"variable": name, "control": values[df.treatment.eq(0)].mean(),
                             "treatment": values[df.treatment.eq(1)].mean(),
                             "standardized_difference": standardized_difference(values[df.treatment.eq(0)], values[df.treatment.eq(1)])})
    balance = pd.DataFrame(balance_rows)

    primary = proportion_effect(control.purchase_24h.sum(), len(control), treatment.purchase_24h.sum(), len(treatment))
    primary["business_hurdle"] = BUSINESS_HURDLE
    primary["ci_excludes_zero"] = bool(primary["ci_low"] > 0 or primary["ci_high"] < 0)
    primary["ci_clears_business_hurdle"] = bool(primary["ci_low"] >= BUSINESS_HURDLE)

    rpu = mean_effect(control.net_revenue_24h, treatment.net_revenue_24h)
    aov = mean_effect(control.loc[control.purchase_24h.eq(1), "order_value"],
                      treatment.loc[treatment.purchase_24h.eq(1), "order_value"])
    refund_assigned = proportion_effect(control.refund_7d.sum(), len(control), treatment.refund_7d.sum(), len(treatment))
    support = proportion_effect(control.support_contact_7d.sum(), len(control), treatment.support_contact_7d.sum(), len(treatment))
    latency = mean_effect(control.checkout_latency_ms, treatment.checkout_latency_ms)
    guardrails = pd.DataFrame([
        {"metric": "Net revenue / assigned user", **rpu},
        {"metric": "Average order value (buyers)", **aov},
        {"metric": "Refunds / assigned user", **refund_assigned},
        {"metric": "Support contacts / assigned user", **support},
        {"metric": "Checkout latency (ms)", **latency},
    ])

    # CUPED uses only the pre-treatment purchase indicator declared before analysis.
    df["purchase_cuped"], theta = cuped_adjust(df.purchase_24h, df.pre_purchase_28d)
    cuped = mean_effect(df.loc[df.treatment.eq(0), "purchase_cuped"], df.loc[df.treatment.eq(1), "purchase_cuped"])
    cuped["theta"] = theta
    cuped["pre_outcome_correlation"] = float(df.purchase_24h.corr(df.pre_purchase_28d))
    cuped["variance_reduction"] = float(1 - df.purchase_cuped.var(ddof=1) / df.purchase_24h.var(ddof=1))
    cuped["unadjusted_se"] = primary["se"]
    cuped["adjusted_se"] = cuped["se"]

    segment_rows = []
    interaction_results = {}
    for segment in ["device_type", "new_vs_returning"]:
        for value, g in df.groupby(segment):
            c, t = g[g.treatment.eq(0)], g[g.treatment.eq(1)]
            effect = proportion_effect(c.purchase_24h.sum(), len(c), t.purchase_24h.sum(), len(t))
            segment_rows.append({"segment": segment, "value": value, "control_n": len(c), "treatment_n": len(t), **effect})
        model = smf.logit(f"purchase_24h ~ treatment * C({segment})", data=df).fit(disp=False)
        term = [x for x in model.params.index if "treatment:C" in x][0]
        interaction_results[segment] = {"log_odds_interaction": float(model.params[term]),
                                        "p_value": float(model.pvalues[term])}
    segments = pd.DataFrame(segment_rows)

    daily = df.groupby(["experiment_day", "experiment_group"]).agg(users=("user_id", "size"), purchases=("purchase_24h", "sum")).reset_index()
    daily["purchase_rate"] = daily.purchases / daily.users
    pivot = daily.pivot(index="experiment_day", columns="experiment_group", values="purchase_rate")
    daily_effect = (pivot.treatment - pivot.control).rename("absolute_effect").reset_index()
    df["week"] = ((df.experiment_day - 1) // 7 + 1).astype(int)
    weekly_rows = []
    for week, g in df.groupby("week"):
        c, t = g[g.treatment.eq(0)], g[g.treatment.eq(1)]
        effect = proportion_effect(c.purchase_24h.sum(), len(c), t.purchase_24h.sum(), len(t))
        weekly_rows.append({"week": week, "control_n": len(c), "treatment_n": len(t), **effect})
    weekly = pd.DataFrame(weekly_rows)
    time_model = smf.logit("purchase_24h ~ treatment * experiment_day", data=df).fit(disp=False)
    time_interaction_p = float(time_model.pvalues["treatment:experiment_day"])

    # Decision-focused figures.
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.errorbar(primary["absolute_effect"] * 100, 0,
                xerr=[[primary["absolute_effect"] * 100 - primary["ci_low"] * 100],
                      [primary["ci_high"] * 100 - primary["absolute_effect"] * 100]],
                fmt="o", markersize=11, capsize=6, color="#20639B")
    ax.axvline(0, color="#555", linewidth=1); ax.axvline(BUSINESS_HURDLE * 100, color="#ED553B", linestyle="--", label="Business hurdle")
    ax.set_yticks([]); ax.set_xlabel("Absolute change in purchase rate (percentage points)")
    ax.set_title("Checkout completion improved, but the interval does not fully clear the business hurdle")
    ax.legend(frameon=False); sns.despine(left=True); fig.savefig(FIGURES / "primary_effect.png"); plt.close(fig)

    plot = guardrails.copy()
    plot["scaled_effect"] = plot.relative_effect * 100
    plot["scaled_low"] = np.where(plot.control.ne(0), plot.ci_low / plot.control * 100, np.nan)
    plot["scaled_high"] = np.where(plot.control.ne(0), plot.ci_high / plot.control * 100, np.nan)
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(plot))
    ax.errorbar(plot.scaled_effect, y, xerr=np.vstack([plot.scaled_effect-plot.scaled_low, plot.scaled_high-plot.scaled_effect]),
                fmt="o", capsize=4, color="#3CAEA3")
    ax.axvline(0, color="#555", linewidth=1); ax.set_yticks(y, plot.metric); ax.invert_yaxis()
    ax.set_xlabel("Relative treatment effect (95% CI, %)")
    ax.set_title("Faster checkout and fewer contacts come with order-value and refund trade-offs")
    sns.despine(); fig.savefig(FIGURES / "guardrail_effects.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    methods = ["Unadjusted", "CUPED-adjusted"]
    effects = np.array([primary["absolute_effect"], cuped["absolute_effect"]]) * 100
    ses = np.array([primary["se"], cuped["se"]]) * 1.96 * 100
    ax.errorbar(effects, methods, xerr=ses, fmt="o", capsize=5, color="#20639B")
    ax.axvline(0, color="#555", linewidth=1); ax.set_xlabel("Absolute purchase-rate effect (95% CI, pp)")
    ax.set_title("CUPED improves precision modestly without changing the estimate")
    sns.despine(); fig.savefig(FIGURES / "cuped_precision.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    labels = segments.segment.str.replace("_", " ").str.title() + ": " + segments.value.str.title()
    y = np.arange(len(segments))
    ax.errorbar(segments.absolute_effect * 100, y,
                xerr=np.vstack([(segments.absolute_effect-segments.ci_low)*100, (segments.ci_high-segments.absolute_effect)*100]),
                fmt="o", capsize=4, color="#20639B")
    ax.axvline(0, color="#555", linewidth=1); ax.set_yticks(y, labels); ax.invert_yaxis()
    ax.set_xlabel("Absolute purchase-rate effect (95% CI, pp)")
    ax.set_title("Subgroup estimates vary, but interaction tests do not justify separate policies")
    sns.despine(); fig.savefig(FIGURES / "segment_effects.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.errorbar(weekly.week, weekly.absolute_effect * 100,
                yerr=np.vstack([(weekly.absolute_effect-weekly.ci_low)*100, (weekly.ci_high-weekly.absolute_effect)*100]),
                fmt="o-", capsize=4, color="#20639B")
    ax.axhline(0, color="#555", linewidth=1); ax.set_xticks(weekly.week)
    ax.set_xlabel("Experiment week"); ax.set_ylabel("Purchase-rate effect (pp)")
    ax.set_title("Weekly estimates fluctuate around a stable effect; no stopping rule was triggered")
    sns.despine(); fig.savefig(FIGURES / "weekly_effect.png"); plt.close(fig)

    balance.to_csv(PROCESSED / "assignment_balance.csv", index=False)
    guardrails.to_csv(PROCESSED / "guardrail_effects.csv", index=False)
    segments.to_csv(PROCESSED / "segment_effects.csv", index=False)
    daily_effect.to_csv(PROCESSED / "daily_effects.csv", index=False)
    weekly.to_csv(PROCESSED / "weekly_effects.csv", index=False)

    summary = {
        "sample_size": len(df), "control_n": len(control), "treatment_n": len(treatment),
        "duration_days": int(df.assignment_date.nunique()), "planned_baseline": PLANNING_BASELINE,
        "planned_mde_absolute": PLANNING_MDE, "business_hurdle_absolute": BUSINESS_HURDLE,
        "alpha": ALPHA, "power": POWER, "required_per_arm": planned["per_arm"], "required_total": planned["total"],
        "srm": srm, "max_abs_standardized_difference": float(balance.standardized_difference.abs().max()),
        "missing_primary": int(df.purchase_24h.isna().sum()), "primary": primary,
        "guardrails": {r.metric: {k: float(r[k]) for k in ["control", "treatment", "absolute_effect", "relative_effect", "ci_low", "ci_high", "p_value"]} for _, r in guardrails.iterrows()},
        "cuped": cuped, "segments": {f"{r.segment}:{r.value}": {k: float(r[k]) for k in ["control", "treatment", "absolute_effect", "ci_low", "ci_high", "p_value"]} for _, r in segments.iterrows()},
        "interaction_tests": interaction_results, "time_interaction_p": time_interaction_p,
        "weekly_effects": {str(int(r.week)): float(r.absolute_effect) for _, r in weekly.iterrows()},
    }
    (PROCESSED / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

