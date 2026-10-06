# Multi-stage production container for DSCI-28 Capstone Microservice
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn[standard] pytest httpx

# Copy project files
COPY . .

# Expose API and Streamlit ports
EXPOSE 8000
EXPOSE 8501

# Default command: launch FastAPI microservice
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
