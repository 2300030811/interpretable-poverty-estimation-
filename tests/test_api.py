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
    assert "status" in data
    assert data["schema_compatibility"] in ("COMPATIBLE", "EXPLORATORY", "INSUFFICIENT")
    assert data["scientific_validation_status"] == "UNVALIDATED_EXTERNAL_DOMAIN"
    assert data["eligibility_determination_permitted"] is False
    assert "domain_shift" in data


def test_api_upload_empty_csv_returns_400():
    """Verify empty CSV upload returns HTTP 400 with sanitized error."""
    response = client.post(
        "/v1/upload-survey",
        files={"file": ("empty.csv", b"", "text/csv")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_api_upload_multi_module():
    """Verify multi-module upload endpoint joins menage and welfare."""
    menage_csv = b"hhid,roof_type,grid_electricity\n1,2,0\n2,3,1\n"
    welfare_csv = b"hhid,family_size,head_age\n1,7,45\n2,3,38\n"

    response = client.post(
        "/v1/upload-multi-module",
        files={
            "menage_file": ("menage.csv", menage_csv, "text/csv"),
            "welfare_file": ("welfare.csv", welfare_csv, "text/csv"),
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["n_households"] == 2
    assert "merge_audit" in data
    assert data["scientific_validation_status"] == "UNVALIDATED_EXTERNAL_DOMAIN"
    assert data["eligibility_determination_permitted"] is False


def test_api_upload_multi_module_zero_overlap_returns_400():
    """Verify zero overlap between required household modules returns HTTP 400."""
    menage_csv = b"hhid,roof_type\n1,2\n2,3\n"
    welfare_csv = b"hhid,family_size\n100,5\n200,4\n"

    response = client.post(
        "/v1/upload-multi-module",
        files={
            "menage_file": ("menage.csv", menage_csv, "text/csv"),
            "welfare_file": ("welfare.csv", welfare_csv, "text/csv"),
        }
    )
    assert response.status_code == 400
    assert "zero overlapping 'hhid' identifiers" in response.json()["detail"].lower()


def test_api_upload_multi_module_conflicting_duplicates_returns_400():
    """Verify conflicting duplicate identifiers return HTTP 400."""
    menage_csv = b"hhid,roof_type\n1,2\n1,5\n2,3\n"

    response = client.post(
        "/v1/upload-multi-module",
        files={
            "menage_file": ("menage.csv", menage_csv, "text/csv"),
        }
    )
    assert response.status_code == 400
    assert "conflicting duplicate records" in response.json()["detail"].lower()


def test_api_predict_unsupported_external_country_marked_unvalidated():
    """Verify single-household prediction for non-EHCVM country marks UNVALIDATED_EXTERNAL_DOMAIN."""
    payload = {
        "country": "Nigeria",
        "features": {"hhsize": 6.0, "elec_ac": 1.0},
        "policy_threshold": 0.35
    }
    response = client.post("/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_supported_country"] is False
    assert data["scientific_validation_status"] == "UNVALIDATED_EXTERNAL_DOMAIN"


def test_api_recourse_unsupported_external_country_marked_unvalidated():
    """Verify recourse generation for non-EHCVM country marks UNVALIDATED_EXTERNAL_DOMAIN."""
    payload = {
        "country": "Nigeria",
        "features": {"hhsize": 10.0, "elec_ac": 0.0},
        "policy_threshold": 0.35
    }
    response = client.post("/v1/recourse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_supported_country"] is False
    assert data["scientific_validation_status"] == "UNVALIDATED_EXTERNAL_DOMAIN"
