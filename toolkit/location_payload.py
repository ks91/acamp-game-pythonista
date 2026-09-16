import uuid
from typing import Any, Optional


def make_location_sample(
    *,
    team_id: str,
    device_id: str,
    client_time: str,
    location: dict[str, Any],
    sample_id: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "team_id": team_id,
        "device_id": device_id,
        "client_time": client_time,
        "sample_id": sample_id or str(uuid.uuid4()),
        "latitude": float(location["latitude"]),
        "longitude": float(location["longitude"]),
        "accuracy_m": float(location["horizontal_accuracy"]),
    }
