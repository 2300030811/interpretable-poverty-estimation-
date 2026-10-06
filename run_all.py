"""
DSCI-28 One-Command Launcher
Starts both the FastAPI REST microservice and the Streamlit dashboard together.
"""
import subprocess
import sys
import time
import os

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    print("=" * 60)
    print("🚀 Launching DSCI-28 Capstone System")
    print("=" * 60)
    print("1. Starting FastAPI Microservice on http://localhost:8000 ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(root_dir, "EHCVM_Project", "EHCVM_Project")

    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8000"],
        env=env
    )
    time.sleep(1.5)

    print("2. Starting Streamlit Dashboard on http://localhost:8501 ...")
    app_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py"],
        env=env
    )

    print("\n✅ All services running!")
    print("• Dashboard UI:  http://localhost:8501")
    print("• API & Swagger: http://localhost:8000/docs")
    print("• Press Ctrl+C in this terminal to shut down both services cleanly.\n")

    try:
        app_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down services...")
        api_proc.terminate()
        app_proc.terminate()

if __name__ == "__main__":
    main()
