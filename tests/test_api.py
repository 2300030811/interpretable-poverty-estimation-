"""
tests/test_api.py — Integration tests for FastAPI REST microservice endpoints.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app

client = TestClient(app)

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data

def test_api_health():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["supported_countries"] >= 8

def test_api_countries():
    response = client.get("/v1/countries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8

def test_api_predict():
    payload = {
        "country": "Benin",
        "features": {
            "hhsize": 8.0,
            "elec_ac": 0.0,
            "sol": 1.0,
            "ind_telpor": 0.0
        },
        "policy_threshold": 0.35
    }
    response = client.post("/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "probability_poor" in data
    assert 0.0 <= data["probability_poor"] <= 1.0
    assert "is_poor_policy" in data

def test_api_recourse():
    payload = {
        "country": "Benin",
        "features": {
            "hhsize": 10.0,
            "elec_ac": 0.0,
            "sol": 1.0,
            "mur": 1.0
        },
        "policy_threshold": 0.35,
        "max_steps": 3
    }
    response = client.post("/v1/recourse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "baseline_probability" in data
    assert "status" in data

def test_api_conformal():
    payload = {
        "probabilities": [0.05, 0.48, 0.92],
        "alpha": 0.10
    }
    response = client.post("/v1/conformal", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 3
    assert data["results"][0]["category"] == "CERTAIN_NON_POOR"
    assert data["results"][2]["category"] == "CERTAIN_POOR"
    assert "q_hat" in data
    assert data["q_hat"] is not None
    assert 0.4 < data["q_hat"] < 0.8

def test_api_conformal_alpha_sensitivity():
    """Verify that changing alpha dynamically recalculates calibrated threshold q_hat."""
    res_05 = client.post("/v1/conformal", json={"probabilities": [0.5], "alpha": 0.05}).json()
    res_20 = client.post("/v1/conformal", json={"probabilities": [0.5], "alpha": 0.20}).json()
    assert res_05["q_hat"] != res_20["q_hat"]
    # Tighter coverage guarantee (smaller alpha) requires higher nonconformity quantile
    assert res_05["q_hat"] > res_20["q_hat"]

def test_api_upload_survey():
    csv_content = b"family_size,grid_electricity,cellphone\n8,0,0\n3,1,2\n"
    response = client.post(
        "/v1/upload-survey",
        files={"file": ("test_survey.csv", csv_content, "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["n_households"] == 2
    assert "policy_headcount_rate" in data
