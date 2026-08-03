"""Unit tests for the simplified -> raw payload translation layer.

The model pipeline is fed by ``perform_data_cleaning`` which ends in
``.dropna()``.  Any field the cleaner cannot parse silently produces an empty
frame rather than an error, so these tests assert the round trip end to end:
simplified input -> raw payload -> cleaned frame -> expected feature values.
"""

import sys
from pathlib import Path
from typing import get_args

import pandas as pd
import pytest
from pydantic import ValidationError

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.api_payload import (  # noqa: E402
    MAX_DISTANCE_KM,
    MIN_ORDER_HOUR,
    RAW_FIELDS,
    CityType,
    OrderType,
    SimplifiedOrder,
    Traffic,
    VehicleType,
    Weather,
    YesNo,
    build_raw_payload,
)
from scripts.data_clean_utils import perform_data_cleaning  # noqa: E402


def make_order(**overrides):
    """A valid baseline order; individual fields overridden per test."""
    defaults = dict(
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
    defaults.update(overrides)
    return SimplifiedOrder(**defaults)


def clean(order):
    """Run an order through payload building and the real cleaning pipeline."""
    payload = build_raw_payload(order)
    return perform_data_cleaning(pd.DataFrame(payload, index=[0]))


# --------------------------------------------------------------------------
# payload shape
# --------------------------------------------------------------------------

def test_payload_has_exactly_the_19_raw_fields():
    payload = build_raw_payload(make_order())
    assert set(payload) == set(RAW_FIELDS)
    assert len(payload) == 19


def test_weather_is_prefixed_for_the_cleaner():
    # the cleaner strips the literal "conditions " prefix
    payload = build_raw_payload(make_order(weather="stormy"))
    assert payload["Weatherconditions"] == "conditions stormy"


def test_longitude_is_held_constant_so_offset_is_along_a_meridian():
    payload = build_raw_payload(make_order(distance_km=12.0))
    assert payload["Restaurant_longitude"] == payload["Delivery_location_longitude"]
    assert payload["Delivery_location_latitude"] > payload["Restaurant_latitude"]


# --------------------------------------------------------------------------
# round trip through the real cleaning pipeline
# --------------------------------------------------------------------------

def test_baseline_order_survives_cleaning():
    assert not clean(make_order()).empty


@pytest.mark.parametrize(
    "distance_km, expected_type",
    [
        (0.5, "short"),
        (3.0, "short"),
        (7.5, "medium"),
        (12.0, "long"),
        (24.9, "very_long"),
        (25.0, "very_long"),
    ],
)
def test_requested_distance_is_reproduced_exactly(distance_km, expected_type):
    cleaned = clean(make_order(distance_km=distance_km))
    assert not cleaned.empty, f"{distance_km} km was dropped by the cleaner"
    assert cleaned["distance"].iloc[0] == pytest.approx(distance_km, abs=1e-6)
    assert cleaned["distance_type"].iloc[0] == expected_type


@pytest.mark.parametrize("pickup_minutes", [1, 10, 45, 60])
def test_pickup_minutes_survive_the_round_trip(pickup_minutes):
    cleaned = clean(make_order(pickup_minutes=pickup_minutes))
    assert cleaned["pickup_time_minutes"].iloc[0] == pytest.approx(pickup_minutes)


@pytest.mark.parametrize(
    "order_hour, expected",
    [
        (7, "morning"),
        (12, "morning"),
        (17, "afternoon"),
        (20, "evening"),
        (23, "night"),
    ],
)
def test_order_hour_maps_to_time_of_day(order_hour, expected):
    cleaned = clean(make_order(order_hour=order_hour))
    assert not cleaned.empty
    assert cleaned["order_time_of_day"].iloc[0] == expected


def test_midnight_wrap_preserves_pickup_minutes():
    # 23:00 + 60min crosses into the next day; pandas' .dt.seconds
    # normalisation still yields the correct positive offset
    cleaned = clean(make_order(order_hour=23, pickup_minutes=60))
    assert not cleaned.empty
    assert cleaned["pickup_time_minutes"].iloc[0] == pytest.approx(60)


@pytest.mark.parametrize(
    "field, value",
    [
        ("weather", "fog"),
        ("traffic", "jam"),
        ("type_of_order", "buffet"),
        ("type_of_vehicle", "electric_scooter"),
        ("city_type", "semi-urban"),
        ("festival", "yes"),
    ],
)
def test_categorical_values_survive_cleaning(field, value):
    cleaned = clean(make_order(**{field: value}))
    assert not cleaned.empty, f"{field}={value} was dropped by the cleaner"


# --------------------------------------------------------------------------
# validation guardrails - these bounds were measured against the cleaner
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "field, value",
    [
        ("distance_km", 25.01),   # > 25 -> distance_type NaN -> dropped
        ("distance_km", 30.0),
        ("distance_km", 0.0),     # zero distance is not a real order
        ("distance_km", -1.0),
        ("age", 17),              # minors are explicitly dropped
        ("age", 0),
        ("ratings", 6.0),         # "6" is explicitly dropped
        ("ratings", 0.5),
        ("pickup_minutes", 0),
        ("pickup_minutes", 61),
        ("order_hour", 0),        # hour 0 is the excluded left bin edge -> NaN
        ("order_hour", 1),        # 1-6 bin to "after_midnight", unseen by the encoder
        ("order_hour", 6),
        ("order_hour", 24),
        ("type_of_vehicle", "bicycle"),  # in the dataset, absent from the encoder
        ("vehicle_condition", 4),
        ("multiple_deliveries", 4),
        ("weather", "hailstorm"),
        ("traffic", "gridlock"),
        ("city_type", "metropolitan"),  # dataset spells it "metropolitian"
    ],
)
def test_invalid_input_is_rejected_by_validation(field, value):
    with pytest.raises(ValidationError):
        make_order(**{field: value})


@pytest.mark.parametrize(
    "field, value",
    [
        ("distance_km", 25.0),
        ("distance_km", 0.1),
        ("age", 18),
        ("ratings", 5.0),
        ("ratings", 1.0),
        ("pickup_minutes", 1),
        ("pickup_minutes", 60),
        ("order_hour", 7),
        ("order_hour", 23),
        ("vehicle_condition", 0),
        ("multiple_deliveries", 0),
    ],
)
def test_boundary_values_are_accepted(field, value):
    order = make_order(**{field: value})
    assert getattr(order, field) == value
    assert not clean(order).empty, f"{field}={value} passed validation but was dropped"


# --------------------------------------------------------------------------
# the accepted values must match what the preprocessor was actually fitted on
#
# The nominal encoder uses handle_unknown="ignore", so a label the encoder has
# never seen does not raise - it becomes an all-zero vector and silently
# degrades the prediction.  These tests are the only thing standing between us
# and that failure mode.
# --------------------------------------------------------------------------

def fitted_categories():
    """Map every encoded column to the set of labels the pipeline knows."""
    joblib = pytest.importorskip("joblib")
    path = ROOT / "models" / "preprocessor.joblib"
    if not path.exists():
        pytest.skip("preprocessor.joblib not available (run `dvc pull`)")

    known = {}
    for _, transformer, columns in joblib.load(path).transformers_:
        if hasattr(transformer, "categories_"):
            for column, cats in zip(columns, transformer.categories_):
                known[column] = set(cats)
    return known


@pytest.mark.parametrize(
    "annotation, column",
    [
        (Weather, "weather"),
        (Traffic, "traffic"),
        (OrderType, "type_of_order"),
        (VehicleType, "type_of_vehicle"),
        (CityType, "city_type"),
        (YesNo, "festival"),
    ],
)
def test_every_accepted_label_is_known_to_the_encoder(annotation, column):
    known = fitted_categories()
    offered = set(get_args(annotation))
    unseen = offered - known[column]
    assert not unseen, (
        f"{column}: {sorted(unseen)} would be silently zero-encoded; "
        f"the pipeline only knows {sorted(known[column])}"
    )


def test_every_allowed_order_hour_maps_to_a_known_time_of_day():
    known = fitted_categories()["order_time_of_day"]
    for hour in range(MIN_ORDER_HOUR, 24):
        cleaned = clean(make_order(order_hour=hour))
        assert not cleaned.empty, f"hour {hour} was dropped by the cleaner"
        tod = cleaned["order_time_of_day"].iloc[0]
        assert tod in known, f"hour {hour} -> {tod!r}, unseen by the encoder"


def test_every_allowed_distance_maps_to_a_known_distance_type():
    known = fitted_categories()["distance_type"]
    for tenths in range(1, int(MAX_DISTANCE_KM * 10) + 1):
        distance = tenths / 10
        cleaned = clean(make_order(distance_km=distance))
        assert not cleaned.empty, f"{distance} km was dropped by the cleaner"
        bucket = cleaned["distance_type"].iloc[0]
        assert bucket in known, f"{distance} km -> {bucket!r}, unseen by the encoder"
