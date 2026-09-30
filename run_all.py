"""Rebuild data, analysis, SQL validation, figures, and executed notebook."""
from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parent
commands = [
    [sys.executable, "-m", "src.generate_data"],
    [sys.executable, "-m", "src.run_analysis"],
    [sys.executable, "-m", "src.build_notebook"],
    [sys.executable, "-m", "src.validate_project"],
    [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", "--ExecutePreprocessor.timeout=600", "notebooks/experiment_analysis.ipynb"],
]
for command in commands:
    print("RUN", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
print("Project reproduced successfully.")

