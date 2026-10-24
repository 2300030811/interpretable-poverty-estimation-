"""
Streamlit Cloud Entry Point
DSCI-28 Capstone Application: Interpretable Cross-Country Well-Being Estimation
"""
import runpy
from pathlib import Path

# Execute main application located in app.py
_app_path = Path(__file__).resolve().parent / "app.py"
runpy.run_path(str(_app_path), run_name="__main__")
