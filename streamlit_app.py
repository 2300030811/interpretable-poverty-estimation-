"""
Streamlit Cloud Entry Point
DSCI-28 Capstone Application: Interpretable Cross-Country Well-Being Estimation
"""
import sys
import runpy
from pathlib import Path

# Evict stale cached in-memory modules if running in persistent Streamlit Cloud container
if "src.adapter" in sys.modules and not hasattr(sys.modules["src.adapter"], "domain_diagnostics"):
    for mod in [m for m in list(sys.modules.keys()) if m == "src" or m.startswith("src.")]:
        del sys.modules[mod]

# Execute main application located in app.py
_app_path = Path(__file__).resolve().parent / "app.py"
runpy.run_path(str(_app_path), run_name="__main__")

