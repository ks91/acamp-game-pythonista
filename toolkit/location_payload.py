from typing import Any


def make_location_sample(
    *,
    team_id: str,
    device_id: str,
    client_time: str,
    sample_id: str,
    location: dict[str, Any],
) -> dict[str, Any]:
    return {
        "team_id": team_id,
        "device_id": device_id,
        "client_time": client_time,
        "sample_id": sample_id,
        "latitude": float(location["latitude"]),
        "longitude": float(location["longitude"]),
        "accuracy_m": float(location["horizontal_accuracy"]),
    }
