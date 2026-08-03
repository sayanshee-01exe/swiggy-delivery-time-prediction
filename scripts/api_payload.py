"""Translate a human-friendly order into the raw Swiggy dataset schema.

The trained pipeline is fed by ``perform_data_cleaning``, which expects the
original 19-column dataset layout: latitude/longitude pairs, rider ids and
order/pickup timestamps.  None of that is reasonable to ask a person for, so
the web form collects a handful of plain fields and this module synthesises
the raw record from them.

Two things make the synthesis non-obvious:

* ``distance`` is not an input to the pipeline - it is derived by a haversine
  over the two coordinate pairs.  To hit a requested distance exactly we pin
  the restaurant at a fixed point and offset the delivery latitude along the
  same meridian, where one degree of latitude is a constant number of km.
* ``perform_data_cleaning`` ends in ``.dropna()``, so an out-of-range value
  produces an empty frame instead of an error.  The bounds below were measured
  against the cleaner so that invalid input is rejected up front with a usable
  message rather than vanishing.
"""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

# Fixed restaurant location (Indore, matching the training data's region).
# Both coordinates sit well above the cleaner's `clean_lat_long` threshold of 1.
RESTAURANT_LAT = 22.745049
RESTAURANT_LON = 75.892471

# Kilometres per degree of latitude, using the same earth radius (6371 km) as
# the pipeline's haversine so the requested distance round-trips exactly.
KM_PER_DEGREE_LAT = 111.19492664455873

# Upper bound of the cleaner's distance_type bins ([0, 5, 10, 15, 25]).
# Anything above this bins to NaN and the row is dropped.
MAX_DISTANCE_KM = 25.0

# The 19 columns of the raw dataset, in dataset order.
RAW_FIELDS = (
    "ID",
    "Delivery_person_ID",
    "Delivery_person_Age",
    "Delivery_person_Ratings",
    "Restaurant_latitude",
    "Restaurant_longitude",
    "Delivery_location_latitude",
    "Delivery_location_longitude",
    "Order_Date",
    "Time_Orderd",
    "Time_Order_picked",
    "Weatherconditions",
    "Road_traffic_density",
    "Vehicle_condition",
    "Type_of_order",
    "Type_of_vehicle",
    "multiple_deliveries",
    "Festival",
    "City",
)

# Every value below must exist in the fitted preprocessor's categories.  The
# nominal encoder uses handle_unknown="ignore", so an unseen label does not
# raise - it silently becomes an all-zero vector and quietly degrades the
# prediction.  tests/unit/test_api_payload.py asserts these stay in sync.
Weather = Literal["sunny", "stormy", "sandstorms", "cloudy", "fog", "windy"]
Traffic = Literal["low", "medium", "high", "jam"]
OrderType = Literal["snack", "meal", "drinks", "buffet"]
# "bicycle" exists in the raw dataset but not in the fitted encoder
VehicleType = Literal["motorcycle", "scooter", "electric_scooter"]
CityType = Literal["metropolitian", "urban", "semi-urban"]
YesNo = Literal["yes", "no"]

# Lowest order hour whose time_of_day bin the encoder actually knows.  Hours
# 1-6 bin to "after_midnight", which the preprocessor was never fitted on.
MIN_ORDER_HOUR = 7


class SimplifiedOrder(BaseModel):
    """What the web form actually asks for.

    Every bound here mirrors a rule inside ``perform_data_cleaning`` that would
    otherwise drop the row silently.
    """

    # > 25 km bins to NaN in distance_type
    distance_km: float = Field(gt=0, le=MAX_DISTANCE_KM)
    # riders under 18 are explicitly dropped as minors
    age: int = Field(ge=18, le=65)
    # a rating of exactly "6" is explicitly dropped
    ratings: float = Field(ge=1.0, le=5.0)
    pickup_minutes: int = Field(ge=1, le=60)
    # Hour 0 lands on the excluded left edge of the time_of_day bins
    # ([0, 6, 12, 17, 20, 24] with right=True) and becomes NaN -> row dropped.
    # Hours 1-6 bin to "after_midnight", which the encoder never saw, so the
    # usable range starts at 7 (the first hour in the "morning" bin).
    order_hour: int = Field(default=13, ge=MIN_ORDER_HOUR, le=23)

    weather: Weather = "sunny"
    traffic: Traffic = "medium"
    vehicle_condition: int = Field(default=2, ge=0, le=3)
    type_of_order: OrderType = "snack"
    type_of_vehicle: VehicleType = "motorcycle"
    multiple_deliveries: int = Field(default=0, ge=0, le=3)
    festival: YesNo = "no"
    city_type: CityType = "metropolitian"


def build_raw_payload(order: SimplifiedOrder, order_date: datetime | None = None) -> dict:
    """Expand a :class:`SimplifiedOrder` into the raw 19-column record.

    ``order_date`` defaults to today, which is what drives the ``is_weekend``
    feature; it is injectable so tests can pin the date.
    """
    order_date = order_date or datetime.now()

    # Offsetting latitude alone keeps the two points on one meridian, so the
    # haversine reduces to the arc length and returns distance_km exactly.
    delivery_lat = RESTAURANT_LAT + order.distance_km / KM_PER_DEGREE_LAT

    ordered_at = order_date.replace(
        hour=order.order_hour, minute=0, second=0, microsecond=0
    )
    picked_at = ordered_at + timedelta(minutes=order.pickup_minutes)

    return {
        # dropped during cleaning, but the column must be present
        "ID": "web-request",
        # the cleaner splits this on "RES" to derive a city name it then drops
        "Delivery_person_ID": "WEBRES01",
        "Delivery_person_Age": str(order.age),
        "Delivery_person_Ratings": str(order.ratings),
        "Restaurant_latitude": RESTAURANT_LAT,
        "Restaurant_longitude": RESTAURANT_LON,
        "Delivery_location_latitude": delivery_lat,
        "Delivery_location_longitude": RESTAURANT_LON,
        "Order_Date": order_date.strftime("%d-%m-%Y"),
        "Time_Orderd": ordered_at.strftime("%H:%M:%S"),
        "Time_Order_picked": picked_at.strftime("%H:%M:%S"),
        # the cleaner strips the literal "conditions " prefix
        "Weatherconditions": f"conditions {order.weather}",
        "Road_traffic_density": order.traffic,
        "Vehicle_condition": order.vehicle_condition,
        "Type_of_order": order.type_of_order,
        "Type_of_vehicle": order.type_of_vehicle,
        "multiple_deliveries": str(order.multiple_deliveries),
        "Festival": order.festival,
        "City": order.city_type,
    }
