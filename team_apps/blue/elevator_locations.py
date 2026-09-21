"""GPS grouping for Blue's human-confirmed elevator discoveries."""

from math import asin, cos, radians, sin, sqrt


_EARTH_RADIUS_M = 6_371_000.0


def _distance_m(first, second):
    latitude_delta = radians(second["latitude"] - first["latitude"])
    longitude_delta = radians(second["longitude"] - first["longitude"])
    first_latitude = radians(first["latitude"])
    second_latitude = radians(second["latitude"])
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * asin(sqrt(haversine))


def classify_location(existing_locations, candidate_location, threshold_m=10):
    """Classify a human-confirmed elevator by horizontal GPS proximity."""
    for index, location in enumerate(existing_locations):
        if _distance_m(location, candidate_location) <= threshold_m:
            return {"kind": "same_position_group", "matching_index": index}
    return {"kind": "new_position_group", "matching_index": None}
