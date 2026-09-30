"""Small, reusable statistical helpers for experiment analysis."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize


def proportion_effect(control_successes, control_n, treatment_successes, treatment_n, alpha=.05):
    p0, p1 = control_successes / control_n, treatment_successes / treatment_n
    diff = p1 - p0
    se = math.sqrt(p0 * (1 - p0) / control_n + p1 * (1 - p1) / treatment_n)
    z = diff / se
    crit = norm.ppf(1 - alpha / 2)
    return {"control": p0, "treatment": p1, "absolute_effect": diff,
            "relative_effect": diff / p0, "se": se, "ci_low": diff - crit * se,
            "ci_high": diff + crit * se, "z": z, "p_value": 2 * norm.sf(abs(z))}


def mean_effect(control, treatment, alpha=.05):
    c, t = np.asarray(control, float), np.asarray(treatment, float)
    diff = t.mean() - c.mean()
    se = math.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c))
    crit = norm.ppf(1 - alpha / 2)
    return {"control": c.mean(), "treatment": t.mean(), "absolute_effect": diff,
            "relative_effect": diff / c.mean() if c.mean() else np.nan, "se": se,
            "ci_low": diff - crit * se, "ci_high": diff + crit * se,
            "p_value": 2 * norm.sf(abs(diff / se))}


def srm_test(control_n, treatment_n, expected_treatment_share=.5):
    total = control_n + treatment_n
    expected = np.array([total * (1 - expected_treatment_share), total * expected_treatment_share])
    observed = np.array([control_n, treatment_n])
    statistic = ((observed - expected) ** 2 / expected).sum()
    return {"chi_square": statistic, "p_value": chi2.sf(statistic, 1)}


def required_sample_size(baseline, mde_absolute, alpha=.05, power=.80):
    effect = abs(proportion_effectsize(baseline + mde_absolute, baseline))
    per_arm = math.ceil(NormalIndPower().solve_power(effect, power=power, alpha=alpha, ratio=1))
    return {"per_arm": per_arm, "total": 2 * per_arm}


def cuped_adjust(outcome, covariate):
    y, x = np.asarray(outcome, float), np.asarray(covariate, float)
    theta = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
    adjusted = y - theta * (x - x.mean())
    return adjusted, theta

