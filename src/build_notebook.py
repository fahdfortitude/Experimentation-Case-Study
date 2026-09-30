"""Build the experiment analysis notebook."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.12"}
nb["cells"] = [
    nbf.v4.new_markdown_cell("# Checkout Experiment — Simplified Checkout Evaluation\n\nThe decision is whether a simplified checkout creates enough incremental customer and business value to ship. The analysis validates assignment before estimating the primary effect, guardrails, pre-specified subgroup effects, and time dynamics."),
    nbf.v4.new_code_cell("from pathlib import Path\nimport json, sys\nimport numpy as np\nimport pandas as pd\nimport statsmodels.formula.api as smf\nROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\nsys.path.insert(0, str(ROOT))\nfrom src.statistics import proportion_effect, mean_effect, srm_test, required_sample_size, cuped_adjust\ndf = pd.read_csv(ROOT/'data/raw/experiment_users.csv', parse_dates=['assignment_timestamp'])\ndf['treatment'] = (df.experiment_group=='treatment').astype(int)\ndf.shape"),
    nbf.v4.new_markdown_cell("## 1. Design and decision rules\n\n- **Unit:** user, assigned once at the first eligible checkout start.\n- **Primary metric:** purchase within 24 hours per assigned user.\n- **Analysis:** intention to treat.\n- **Duration:** fixed 28 days; no significance-based stopping.\n- **Planning:** 45% baseline, 1.5 percentage-point MDE, 5% two-sided alpha, 80% power.\n- **Business hurdle:** 0.75 percentage point. This is distinct from the statistical MDE."),
    nbf.v4.new_code_cell("required_sample_size(.45, .015, alpha=.05, power=.80)"),
    nbf.v4.new_markdown_cell("## 2. Experiment health before outcomes\n\nSRM, assignment balance, eligibility, missingness, and duration are checked before interpreting treatment effects. A passed SRM test does not prove flawless randomization; it removes one important warning sign."),
    nbf.v4.new_code_cell("counts = df.experiment_group.value_counts()\nsrm_test(counts['control'], counts['treatment'])"),
    nbf.v4.new_code_cell("balance = pd.read_csv(ROOT/'data/processed/assignment_balance.csv')\nbalance.style.format({'control':'{:.3f}','treatment':'{:.3f}','standardized_difference':'{:.3f}'})"),
    nbf.v4.new_markdown_cell("There is no evidence of SRM (p=0.812), required fields are complete, and the largest absolute standardized difference is 0.024. The realized sample exceeds the planned requirement."),
    nbf.v4.new_markdown_cell("## 3. Primary result\n\nThe primary estimate is the difference in user-level purchase proportions. The confidence interval is considered against both zero and the separate business hurdle."),
    nbf.v4.new_code_cell("c, t = df[df.treatment==0], df[df.treatment==1]\nprimary = proportion_effect(c.purchase_24h.sum(), len(c), t.purchase_24h.sum(), len(t))\npd.Series(primary)"),
    nbf.v4.new_markdown_cell("Treatment increased checkout completion from 47.02% to 48.23%: +1.21 percentage points (95% CI +0.32 to +2.10; p=0.008). The experiment provides evidence of product efficacy. Because the interval includes effects below and above the 0.75-point commercial hurdle, the commercially relevant magnitude remains uncertain. The hurdle informs the holistic decision; it is not a universal confidence-interval shipping rule."),
    nbf.v4.new_markdown_cell("## 4. Guardrails and business value"),
    nbf.v4.new_code_cell("guardrails = pd.read_csv(ROOT/'data/processed/guardrail_effects.csv')\nguardrails[['metric','control','treatment','absolute_effect','relative_effect','ci_low','ci_high','p_value']].style.format(precision=3)"),
    nbf.v4.new_markdown_cell("Latency and support contacts improve. Average order value falls £1.89 (95% CI −£3.08 to −£0.70), while refunds per assigned user rise 0.35 percentage points (95% CI +0.09 to +0.60). Net revenue per assigned user changes by −£0.02 (95% CI −£1.06 to +£1.01), providing no demonstrated commercial gain. These trade-offs prevent a conversion-only ship decision. AOV among buyers is conditional on a post-treatment event—and treatment changes buyer composition—so revenue per assigned user receives more decision weight."),
    nbf.v4.new_markdown_cell("## 5. CUPED variance reduction\n\nThe declared pre-period purchase indicator is correlated with the outcome but cannot be affected by treatment."),
    nbf.v4.new_code_cell("adjusted, theta = cuped_adjust(df.purchase_24h, df.pre_purchase_28d)\ndf['purchase_cuped'] = adjusted\nunadjusted = proportion_effect(c.purchase_24h.sum(), len(c), t.purchase_24h.sum(), len(t))\nadjusted_effect = mean_effect(df.loc[df.treatment==0,'purchase_cuped'], df.loc[df.treatment==1,'purchase_cuped'])\n{'correlation':df.purchase_24h.corr(df.pre_purchase_28d), 'theta':theta, 'unadjusted_se':unadjusted['se'], 'adjusted_se':adjusted_effect['se'], 'adjusted_effect':adjusted_effect['absolute_effect']}"),
    nbf.v4.new_markdown_cell("CUPED reduces variance by only 1.15% because the pre-period covariate has weak correlation (0.107). It modestly improves precision and leaves the conclusion unchanged. CUPED cannot repair broken assignment, missing outcomes, or post-treatment bias."),
    nbf.v4.new_markdown_cell("## 6. Pre-specified heterogeneity"),
    nbf.v4.new_code_cell("segments = pd.read_csv(ROOT/'data/processed/segment_effects.csv')\nsegments[['segment','value','control','treatment','absolute_effect','ci_low','ci_high','p_value']].style.format({'control':'{:.1%}','treatment':'{:.1%}','absolute_effect':'{:.2%}','ci_low':'{:.2%}','ci_high':'{:.2%}','p_value':'{:.3f}'})"),
    nbf.v4.new_markdown_cell("Point estimates are larger for mobile and new users, but the direct interaction tests are not conclusive (p=0.163 and p=0.179). A significant estimate in one subgroup and a non-significant estimate in another does not establish a difference between them. The evidence does not support segment-specific shipping."),
    nbf.v4.new_markdown_cell("## 7. Time dynamics and decision"),
    nbf.v4.new_code_cell("weekly = pd.read_csv(ROOT/'data/processed/weekly_effects.csv')\nweekly[['week','control','treatment','absolute_effect','ci_low','ci_high']].style.format({'control':'{:.1%}','treatment':'{:.1%}','absolute_effect':'{:.2%}','ci_low':'{:.2%}','ci_high':'{:.2%}'})"),
    nbf.v4.new_markdown_cell("Weekly effects fluctuate, as expected, but there is no evidence of a linear treatment-by-day trend (p=0.894). The fixed-duration estimate is primary; repeatedly testing cumulative results and stopping at the first p<0.05 would inflate false positives.\n\n**Decision: iterate and retest.** The experiment establishes checkout efficacy more strongly than commercial value. Preserve the latency and support improvements, investigate the refund increase and order-value decline, and test a revised checkout. This decision follows the combined primary, revenue, and guardrail evidence—not a mechanical confidence-interval rule. Do not claim a mobile-only win from these subgroup results."),
]
path = ROOT / "notebooks/experiment_analysis.ipynb"
path.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, path)
print(path)

