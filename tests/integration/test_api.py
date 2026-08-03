"""Integration tests for the FastAPI serving layer.

These run against the real sklearn pipeline built from the local artifacts in
``models/``, so a prediction here exercises the whole chain -- request
validation, payload synthesis, ``perform_data_cleaning`` and the regressor --
without needing network access or a DagsHub token.

``app`` must therefore be importable without contacting the model registry;
the registry load happens on startup, not at import time.
"""

import sys
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn import set_config
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

set_config(transform_output="pandas")

import app as app_module  # noqa: E402

MODELS = ROOT / "models"


def local_loader():
    """Stand-in for the registry loader, using the DVC-tracked artifacts."""
    pipeline = Pipeline(
        steps=[
            ("preprocess", joblib.load(MODELS / "preprocessor.joblib")),
            ("regressor", joblib.load(MODELS / "model.joblib")),
        ]
    )
    return pipeline, "local-artifact-model"


def valid_order(**overrides):
    payload = dict(
        distance_km=7.5,
        age=28,
        ratings=4.6,
        pickup_minutes=10,
        order_hour=13,
        weather="sunny",
        traffic="medium",
        vehicle_condition=2,
        type_of_order="snack",
        type_of_vehicle="motorcycle",
        multiple_deliveries=1,
        festival="no",
        city_type="metropolitian",
    )
    payload.update(overrides)
    return payload


@pytest.fixture(scope="module")
def client():
    if not (MODELS / "model.joblib").exists():
        pytest.skip("model artifacts not available (run `dvc pull`)")
    app_module.load_model(loader=local_loader)
    return TestClient(app_module.app)


@pytest.fixture
def broken_client():
    """A client whose model failed to load, to exercise the degraded path."""

    def boom():
        raise RuntimeError("registry unreachable")

    app_module.load_model(loader=boom)
    yield TestClient(app_module.app)
    app_module.load_model(loader=local_loader)


# --------------------------------------------------------------------------
# health
# --------------------------------------------------------------------------

def test_health_reports_a_loaded_model(client):
    response = client.get("/api/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model_name"] == "local-artifact-model"
    assert body["error"] is None


def test_health_reports_a_failed_model_load(broken_client):
    response = broken_client.get("/api/health")
    # still 200 so the UI can tell "API up, model down" apart from a
    # network failure, which is a different badge state
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "degraded"
    assert body["model_loaded"] is False
    assert "registry unreachable" in body["error"]


# --------------------------------------------------------------------------
# predictions
# --------------------------------------------------------------------------

def test_predict_returns_a_plausible_duration(client):
    response = client.post("/api/predict", json=valid_order())
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body["prediction_minutes"], float)
    # sanity band: a 7.5 km order cannot take 0 or 5 hours
    assert 5 < body["prediction_minutes"] < 120


def test_predict_echoes_the_rounded_value_only_once(client):
    body = client.post("/api/predict", json=valid_order()).json()
    assert set(body) == {"prediction_minutes"}


@pytest.mark.parametrize("distance_km", [0.5, 3.0, 12.0, 25.0])
def test_predict_accepts_the_full_distance_range(client, distance_km):
    response = client.post(
        "/api/predict", json=valid_order(distance_km=distance_km)
    )
    assert response.status_code == 200, response.text
    assert response.json()["prediction_minutes"] > 0


def test_longer_distance_predicts_a_longer_time(client):
    short = client.post(
        "/api/predict", json=valid_order(distance_km=2.0)
    ).json()["prediction_minutes"]
    long = client.post(
        "/api/predict", json=valid_order(distance_km=20.0)
    ).json()["prediction_minutes"]
    assert long > short, "a 20 km order should not be faster than a 2 km one"


@pytest.mark.parametrize(
    "field, value",
    [
        ("distance_km", 25.01),
        ("age", 17),
        ("ratings", 6),
        ("order_hour", 3),
        ("type_of_vehicle", "bicycle"),
        ("weather", "hailstorm"),
    ],
)
def test_predict_rejects_out_of_range_input(client, field, value):
    response = client.post("/api/predict", json=valid_order(**{field: value}))
    assert response.status_code == 422
    # the message should name the offending field, not just say "invalid"
    assert field in response.text


def test_predict_returns_503_when_the_model_is_unavailable(broken_client):
    response = broken_client.post("/api/predict", json=valid_order())
    assert response.status_code == 503
    assert "model" in response.json()["detail"].lower()


# --------------------------------------------------------------------------
# the pre-existing surface must keep working
# --------------------------------------------------------------------------

def test_home_endpoint_still_works(client):
    response = client.get("/")
    assert response.status_code == 200


def test_raw_predict_endpoint_still_works(client):
    raw = {
        "ID": "0xb379",
        "Delivery_person_ID": "BANGRES18DEL02",
        "Delivery_person_Age": "34",
        "Delivery_person_Ratings": "4.5",
        "Restaurant_latitude": 12.913041,
        "Restaurant_longitude": 77.683237,
        "Delivery_location_latitude": 13.043041,
        "Delivery_location_longitude": 77.813237,
        "Order_Date": "19-03-2022",
        "Time_Orderd": "19:45:00",
        "Time_Order_picked": "19:50:00",
        "Weatherconditions": "conditions Sunny",
        "Road_traffic_density": "Jam ",
        "Vehicle_condition": 2,
        "Type_of_order": "Snack ",
        "Type_of_vehicle": "motorcycle ",
        "multiple_deliveries": "1",
        "Festival": "No ",
        "City": "Metropolitian ",
    }
    response = client.post("/predict", json=raw)
    assert response.status_code == 200, response.text
    assert response.json()["prediction"] > 0
