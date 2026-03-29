#!/usr/bin/env python3
"""
Print compact Traccar location context for daily-summary interviews.

Configuration is read from environment variables or an optional
`<private-repo>/.tokens/traccar.env` file:

- TRACCAR_BASE_URL
- TRACCAR_EMAIL
- TRACCAR_PASSWORD
- TRACCAR_DEVICE_ID (preferred)
- TRACCAR_DEVICE_NAME (fallback if device id is omitted)

If configuration is missing or the server is unreachable, this script prints a
short skip message and exits successfully so the daily workflow stays usable.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
TOKENS_FILE = ROOT / ".tokens" / "traccar.env"
PLACES_FILE = ROOT / ".tokens" / "location_places.json"
LOCAL_TZ = datetime.now().astimezone().tzinfo


@dataclass
class TraccarConfig:
    base_url: str
    email: str
    password: str
    device_id: str


@dataclass
class Position:
    timestamp: datetime
    latitude: float
    longitude: float
    speed_kph: float
    address: str


@dataclass
class SavedPlace:
    name: str
    latitude: float
    longitude: float
    radius_m: float


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def build_config() -> TraccarConfig | None:
    load_env_file(TOKENS_FILE)
    base_url = os.environ.get("TRACCAR_BASE_URL", "").strip().rstrip("/")
    email = os.environ.get("TRACCAR_EMAIL", "").strip()
    password = os.environ.get("TRACCAR_PASSWORD", "").strip()
    device_id = os.environ.get("TRACCAR_DEVICE_ID", "").strip()
    device_name = os.environ.get("TRACCAR_DEVICE_NAME", "").strip()

    if not base_url or not email or not password:
        return None

    if not device_id:
        device_id = resolve_device_id(base_url, email, password, device_name)
        if not device_id:
            return None

    return TraccarConfig(
        base_url=base_url,
        email=email,
        password=password,
        device_id=device_id,
    )


def auth_header(email: str, password: str) -> str:
    encoded = base64.b64encode(f"{email}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def api_get_json(base_url: str, email: str, password: str, path: str, params: dict[str, str]) -> Any:
    query = parse.urlencode(params)
    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{query}"
    req = request.Request(url)
    req.add_header("Authorization", auth_header(email, password))
    req.add_header("Accept", "application/json")
    with request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve_device_id(base_url: str, email: str, password: str, device_name: str) -> str:
    if not device_name:
        return ""
    try:
        devices = api_get_json(base_url, email, password, "/api/devices", {})
    except Exception:
        return ""
    device_name_lower = device_name.lower()
    for device in devices:
        name = str(device.get("name", "")).lower()
        unique_id = str(device.get("uniqueId", "")).lower()
        if device_name_lower in {name, unique_id}:
            device_id = device.get("id")
            return str(device_id) if device_id is not None else ""
    return ""


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is not None and LOCAL_TZ is not None:
        return parsed.astimezone(LOCAL_TZ)
    if parsed.tzinfo is None and LOCAL_TZ is not None:
        return parsed.replace(tzinfo=LOCAL_TZ)
    return parsed


def fetch_positions(config: TraccarConfig, day_text: str) -> list[Position]:
    target_day = datetime.strptime(day_text, "%Y-%m-%d").date()
    start_dt = datetime.combine(target_day, time.min)
    end_dt = datetime.combine(target_day + timedelta(days=1), time.min)
    if LOCAL_TZ is not None:
        start_dt = start_dt.replace(tzinfo=LOCAL_TZ)
        end_dt = end_dt.replace(tzinfo=LOCAL_TZ)

    payload = api_get_json(
        config.base_url,
        config.email,
        config.password,
        "/api/reports/route",
        {
            "deviceId": config.device_id,
            "from": start_dt.isoformat(),
            "to": end_dt.isoformat(),
        },
    )

    positions: list[Position] = []
    for row in payload:
        timestamp = parse_timestamp(str(row.get("fixTime") or row.get("deviceTime") or row.get("serverTime") or ""))
        latitude = parse_float(row.get("latitude"))
        longitude = parse_float(row.get("longitude"))
        if timestamp is None or latitude is None or longitude is None:
            continue
        speed_knots = parse_float(row.get("speed")) or 0.0
        positions.append(
            Position(
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                speed_kph=speed_knots * 1.852,
                address=str(row.get("address") or "").strip(),
            )
        )
    return positions


def load_places(path: Path) -> list[SavedPlace]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    places: list[SavedPlace] = []
    if not isinstance(payload, list):
        return places
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        latitude = parse_float(item.get("latitude"))
        longitude = parse_float(item.get("longitude"))
        radius_m = parse_float(item.get("radius_m")) or 100.0
        if not name or latitude is None or longitude is None:
            continue
        places.append(
            SavedPlace(
                name=name,
                latitude=latitude,
                longitude=longitude,
                radius_m=radius_m,
            )
        )
    return places


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def haversine_km(a: Position, b: Position) -> float:
    radius_km = 6371.0
    lat1 = math.radians(a.latitude)
    lon1 = math.radians(a.longitude)
    lat2 = math.radians(b.latitude)
    lon2 = math.radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(x))


def haversine_km_to_coords(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(x))


def nearest_saved_place(position: Position, places: list[SavedPlace]) -> tuple[SavedPlace, float] | None:
    best: tuple[SavedPlace, float] | None = None
    for place in places:
        dist_m = haversine_km_to_coords(
            position.latitude,
            position.longitude,
            place.latitude,
            place.longitude,
        ) * 1000.0
        if dist_m <= place.radius_m:
            if best is None or dist_m < best[1]:
                best = (place, dist_m)
    return best


def summarize_stop_clusters(positions: list[Position], places: list[SavedPlace]) -> list[str]:
    if not positions:
        return []
    clusters: list[tuple[Position, Position, list[Position]]] = []
    current = [positions[0]]
    for pos in positions[1:]:
        if haversine_km(current[-1], pos) <= 0.25:
            current.append(pos)
            continue
        clusters.append((current[0], current[-1], current))
        current = [pos]
    clusters.append((current[0], current[-1], current))

    summaries: list[str] = []
    for start, end, cluster in clusters:
        dwell_minutes = int((end.timestamp - start.timestamp).total_seconds() / 60)
        if dwell_minutes < 20:
            continue
        saved = nearest_saved_place(start, places)
        address = next((p.address for p in cluster if p.address), "")
        if saved is not None:
            label = saved[0].name
        elif address:
            label = address
        else:
            label = f"{start.latitude:.4f}, {start.longitude:.4f}"
        summaries.append(
            f"{start.timestamp.strftime('%H:%M')}-{end.timestamp.strftime('%H:%M')} | {label}"
        )
    return summaries[:5]


def print_summary(day_text: str, positions: list[Position], places: list[SavedPlace]) -> None:
    print(f"Location context for {day_text}:")
    if not positions:
        print("- No Traccar positions found for this date.")
        return

    total_distance_km = 0.0
    moving_points = 0
    max_speed = 0.0
    for prev, cur in zip(positions, positions[1:]):
        total_distance_km += haversine_km(prev, cur)
        if cur.speed_kph >= 5:
            moving_points += 1
        max_speed = max(max_speed, cur.speed_kph)

    first = positions[0]
    last = positions[-1]
    current_place = nearest_saved_place(last, places)
    print(f"- Position samples: {len(positions)}")
    print(f"- First seen: {first.timestamp.strftime('%H:%M')} | {first.latitude:.4f}, {first.longitude:.4f}")
    print(f"- Last seen: {last.timestamp.strftime('%H:%M')} | {last.latitude:.4f}, {last.longitude:.4f}")
    if current_place is not None:
        print(f"- Current place label: {current_place[0].name} ({current_place[1]:.0f} m from saved point)")
    print(f"- Approx travel distance: {total_distance_km:.1f} km")
    print(f"- Moving samples: {moving_points}")
    print(f"- Peak observed speed: {max_speed:.1f} km/h")

    stops = summarize_stop_clusters(positions, places)
    if stops:
        print(f"- Longer stops: {len(stops)}")
        for stop in stops:
            print(f"  - {stop}")
    else:
        print("- Longer stops: none identified from current samples")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print Traccar location context for a target date.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    config = build_config()
    if config is None:
        print(f"Location context for {args.date}: skipped (set TRACCAR_BASE_URL, TRACCAR_EMAIL, TRACCAR_PASSWORD, and TRACCAR_DEVICE_ID or TRACCAR_DEVICE_NAME).")
        return 0

    try:
        positions = fetch_positions(config, args.date)
    except error.HTTPError as exc:
        print(f"Location context for {args.date}: skipped (Traccar HTTP {exc.code}).")
        return 0
    except error.URLError as exc:
        print(f"Location context for {args.date}: skipped ({exc.reason}).")
        return 0
    except Exception as exc:
        print(f"Location context for {args.date}: skipped ({exc.__class__.__name__}).")
        return 0

    places = load_places(PLACES_FILE)
    print_summary(args.date, positions, places)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
