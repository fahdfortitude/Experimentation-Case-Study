"""Execute SQL and reconcile public claims with computed outputs."""
from pathlib import Path
import json
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
raw = ROOT / "data/raw/experiment_users.csv"
con = duckdb.connect()
con.execute(f"CREATE VIEW experiment_users AS SELECT * FROM read_csv_auto('{raw.as_posix()}')")
for path in sorted((ROOT / "sql").glob("*.sql")):
    result = con.execute(path.read_text(encoding="utf-8")).fetchdf()
    assert len(result) > 0, path.name
    print(f"PASS {path.name}: {len(result)} row(s)")

summary = json.loads((ROOT / "data/processed/summary.json").read_text(encoding="utf-8"))
users = pd.read_csv(raw)
assert users.user_id.is_unique
assert users.checkout_started.eq(1).all()
assert users.experiment_group.isin(["control", "treatment"]).all()
assert {"pre_purchase_28d", "pre_revenue_28d", "pre_sessions_28d"}.issubset(users.columns)
assert summary["sample_size"] == summary["control_n"] + summary["treatment_n"] == 48_000
assert summary["duration_days"] == 28
assert summary["required_total"] == 34_630
assert summary["srm"]["p_value"] > .05
assert summary["missing_primary"] == 0
assert summary["primary"]["control"] < summary["primary"]["treatment"]
assert summary["cuped"]["adjusted_se"] < summary["cuped"]["unadjusted_se"]
assert summary["cuped"]["variance_reduction"] > 0
for figure in ["primary_effect.png", "guardrail_effects.png", "cuped_precision.png", "segment_effects.png", "weekly_effect.png"]:
    assert (ROOT / "outputs/figures" / figure).stat().st_size > 10_000
readme = (ROOT / "README.md").read_text(encoding="utf-8")
for value in ["48,000", "47.02%", "48.23%", "1.21 percentage points", "0.812", "1.15%",
              "95% CI −£1.06 to +£1.01", "95% CI −£3.08 to −£0.70",
              "95% CI +0.09 to +0.60 pp", "95% CI −1.57 to −0.64 pp"]:
    assert value in readme, f"README missing {value}"
print("PASS calculations, README reconciliation, and figures")

