@echo off
echo ============================================================
echo   Starting DSCI-28 Capstone Services
echo ============================================================
set PYTHONPATH=%cd%\EHCVM_Project\EHCVM_Project
start "DSCI-28 FastAPI Microservice (Port 8000)" cmd /k python -m uvicorn api.main:app --port 8000
timeout /t 2 >nul
start "DSCI-28 Streamlit Dashboard (Port 8501)" cmd /k streamlit run app.py
echo Services launched!
echo Streamlit Dashboard: http://localhost:8501
echo Swagger REST API:    http://localhost:8000/docs
