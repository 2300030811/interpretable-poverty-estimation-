# Multi-stage production container for DSCI-28 Capstone Platform
FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies required for LightGBM/OpenMP
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Python & module discovery
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/EHCVM_Project/EHCVM_Project:/app" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

# Copy dependency specifications and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy complete project code & assets
COPY . .

# Expose API (8000) and Streamlit (8501) ports
EXPOSE 8000 8501

# Default command: launch all-in-one runner
CMD ["python", "run_all.py"]
