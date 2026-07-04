#!/usr/bin/env python3
"""
Print compact location context for daily-summary interviews.

OwnTracks/S3 configuration is read from environment variables or an optional
location repository `.tokens/location-ingest.env` file. Traccar fallback
configuration is read from environment variables or an optional private-repo
`.tokens/traccar.env` file:

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
import hashlib
import json
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from repo_paths import resolve_private_repo_root

ROOT = resolve_private_repo_root()
TOKENS_FILE = ROOT / ".tokens" / "traccar.env"
LOCATION_REPO_MARKER = ".location-repo.json"
LOCATION_REPO_ENV_KEYS = ("LOCATION_REPO_ROOT", "GEORGE_LOCATION_ROOT")
LEGACY_LOCATION_INGEST_FILE = ROOT / ".tokens" / "location-ingest.env"
LEGACY_PLACES_FILE = ROOT / ".tokens" / "location_places.json"
TRACCAR_CACHE_DIR = ROOT / ".cache" / "traccar"
LOCAL_TZ = datetime.now().astimezone().tzinfo
GEOCODER_USER_AGENT = "georgeskills-journal-ops/1.0"


@dataclass
class TraccarConfig:
    base_url: str
    email: str
    password: str
    device_id: str


@dataclass
class OwnTracksS3Config:
    bucket: str
    prefix: str
    region: str


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
    category: str = ""
    aliases: list[str] | None = None


@dataclass
class StopWindow:
    start: Position
    end: Position
    points: list[Position]


@dataclass
class ReportStop:
    start: datetime
    end: datetime
    latitude: float
    longitude: float
    address: str


STATIONARY_SPEED_KPH = 3.0
STOP_RADIUS_M = 120.0
MIN_STOP_MINUTES = 8
CACHE_TTL_SECONDS = 300


def resolve_location_repo_root() -> Path | None:
    for key in LOCATION_REPO_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        candidate = Path(value).expanduser().resolve()
        if candidate.exists():
            return candidate

    for parent in (ROOT, ROOT.parent):
        try:
            children = [parent, *parent.iterdir()]
        except OSError:
            children = [parent]
        for child in children:
            if child.is_dir() and (child / LOCATION_REPO_MARKER).exists():
                return child.resolve()
    return None


LOCATION_REPO_ROOT = resolve_location_repo_root()
LOCATION_INGEST_FILE = (
    LOCATION_REPO_ROOT / ".tokens" / "location-ingest.env"
    if LOCATION_REPO_ROOT is not None
    else LEGACY_LOCATION_INGEST_FILE
)
PLACES_FILE = (
    LOCATION_REPO_ROOT / ".tokens" / "location_places.json"
    if LOCATION_REPO_ROOT is not None and (LOCATION_REPO_ROOT / ".tokens" / "location_places.json").exists()
    else LEGACY_PLACES_FILE
)


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


def build_owntracks_s3_config() -> OwnTracksS3Config | None:
    load_env_file(LOCATION_INGEST_FILE)
    bucket = os.environ.get("LOCATION_INGEST_S3_BUCKET", "").strip()
    prefix = os.environ.get("LOCATION_INGEST_S3_PREFIX", "owntracks/raw/").strip()
    region = os.environ.get("LOCATION_INGEST_AWS_REGION", "").strip()
    if not bucket:
        return None
    return OwnTracksS3Config(bucket=bucket, prefix=prefix.strip("/"), region=region)


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


def cache_ttl_seconds() -> int:
    raw = os.environ.get("TRACCAR_CACHE_TTL_SECONDS", "").strip()
    if not raw:
        return CACHE_TTL_SECONDS
    try:
        return max(0, int(raw))
    except ValueError:
        return CACHE_TTL_SECONDS


def cache_path(endpoint: str, device_id: str, day_text: str) -> Path:
    key = hashlib.sha1(f"{endpoint}|{device_id}|{day_text}".encode("utf-8")).hexdigest()[:12]
    return TRACCAR_CACHE_DIR / day_text / f"{endpoint}_{device_id}_{key}.json"


def load_cached_json(endpoint: str, device_id: str, day_text: str) -> Any | None:
    ttl = cache_ttl_seconds()
    if ttl <= 0:
        return None
    path = cache_path(endpoint, device_id, day_text)
    if not path.exists():
        return None
    age = datetime.now().timestamp() - path.stat().st_mtime
    if age > ttl:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_cached_json(endpoint: str, device_id: str, day_text: str, payload: Any) -> None:
    ttl = cache_ttl_seconds()
    if ttl <= 0:
        return
    path = cache_path(endpoint, device_id, day_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def fetch_public_json(url: str) -> Any:
    req = request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", GEOCODER_USER_AGENT)
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

    payload = load_cached_json("route", config.device_id, day_text)
    if payload is None:
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
        save_cached_json("route", config.device_id, day_text, payload)

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


def fetch_report_stops(config: TraccarConfig, day_text: str) -> list[ReportStop]:
    target_day = datetime.strptime(day_text, "%Y-%m-%d").date()
    start_dt = datetime.combine(target_day, time.min)
    end_dt = datetime.combine(target_day + timedelta(days=1), time.min)
    if LOCAL_TZ is not None:
        start_dt = start_dt.replace(tzinfo=LOCAL_TZ)
        end_dt = end_dt.replace(tzinfo=LOCAL_TZ)

    payload = load_cached_json("stops", config.device_id, day_text)
    if payload is None:
        payload = api_get_json(
            config.base_url,
            config.email,
            config.password,
            "/api/reports/stops",
            {
                "deviceId": config.device_id,
                "from": start_dt.isoformat(),
                "to": end_dt.isoformat(),
            },
        )
        save_cached_json("stops", config.device_id, day_text, payload)

    stops: list[ReportStop] = []
    for row in payload:
        start = parse_timestamp(str(row.get("startTime") or ""))
        end = parse_timestamp(str(row.get("endTime") or ""))
        latitude = parse_float(row.get("latitude"))
        longitude = parse_float(row.get("longitude"))
        if start is None or end is None or latitude is None or longitude is None:
            continue
        stops.append(
            ReportStop(
                start=start,
                end=end,
                latitude=latitude,
                longitude=longitude,
                address=str(row.get("address") or "").strip(),
            )
        )
    return stops


def aws_cli_json(args: list[str]) -> Any:
    argv = ["aws", *args, "--output", "json"]
    proc = subprocess.run(argv, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"aws exited {proc.returncode}")
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)


def owntracks_s3_day_prefixes(config: OwnTracksS3Config, day_text: str) -> list[str]:
    target_day = datetime.strptime(day_text, "%Y-%m-%d").date()
    days = [target_day - timedelta(days=1), target_day, target_day + timedelta(days=1)]
    return [
        f"{config.prefix}/year={day.year:04d}/month={day.month:02d}/day={day.day:02d}/"
        for day in days
    ]


def list_owntracks_s3_keys(config: OwnTracksS3Config, day_text: str) -> list[str]:
    keys: list[str] = []
    region_args = ["--region", config.region] if config.region else []
    for prefix in owntracks_s3_day_prefixes(config, day_text):
        token: str | None = None
        while True:
            args = [
                "s3api",
                "list-objects-v2",
                "--bucket",
                config.bucket,
                "--prefix",
                prefix,
                *region_args,
            ]
            if token:
                args.extend(["--continuation-token", token])
            payload = aws_cli_json(args)
            for item in payload.get("Contents") or []:
                key = str(item.get("Key") or "")
                if key.endswith(".json"):
                    keys.append(key)
            token = payload.get("NextContinuationToken")
            if not token:
                break
    return sorted(set(keys))


def get_owntracks_s3_record(config: OwnTracksS3Config, key: str) -> dict[str, Any] | None:
    region_args = ["--region", config.region] if config.region else []
    with tempfile.NamedTemporaryFile() as temp:
        aws_cli_json(
            [
                "s3api",
                "get-object",
                "--bucket",
                config.bucket,
                "--key",
                key,
                temp.name,
                *region_args,
            ]
        )
        try:
            payload = json.loads(Path(temp.name).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    if isinstance(payload, dict):
        return payload
    return None


def owntracks_timestamp(payload: dict[str, Any], record: dict[str, Any]) -> datetime | None:
    tst = parse_float(payload.get("tst"))
    if tst is not None:
        parsed = datetime.fromtimestamp(tst, tz=LOCAL_TZ)
        if LOCAL_TZ is not None:
            return parsed.astimezone(LOCAL_TZ)
        return parsed
    received = parse_timestamp(str(record.get("received_at") or ""))
    return received


def owntracks_position_from_record(record: dict[str, Any]) -> Position | None:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    timestamp = owntracks_timestamp(payload, record)
    latitude = parse_float(first_present(payload.get("lat"), payload.get("latitude")))
    longitude = parse_float(first_present(payload.get("lon"), payload.get("longitude")))
    if timestamp is None or latitude is None or longitude is None:
        return None
    speed_kph = parse_float(first_present(payload.get("vel"), payload.get("speed"))) or 0.0
    return Position(
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        speed_kph=speed_kph,
        address="",
    )


def fetch_owntracks_s3_positions(config: OwnTracksS3Config, day_text: str) -> list[Position]:
    target_day = datetime.strptime(day_text, "%Y-%m-%d").date()
    positions: list[Position] = []
    for key in list_owntracks_s3_keys(config, day_text):
        record = get_owntracks_s3_record(config, key)
        if record is None:
            continue
        position = owntracks_position_from_record(record)
        if position is None:
            continue
        if position.timestamp.date() == target_day:
            positions.append(position)
    positions.sort(key=lambda item: item.timestamp)
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
                category=str(item.get("category") or "").strip(),
                aliases=[
                    str(alias).strip()
                    for alias in item.get("aliases", [])
                    if str(alias).strip()
                ] if isinstance(item.get("aliases"), list) else [],
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


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
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


def nearest_saved_place_for_coords(latitude: float, longitude: float, places: list[SavedPlace]) -> tuple[SavedPlace, float] | None:
    best: tuple[SavedPlace, float] | None = None
    for place in places:
        dist_m = haversine_km_to_coords(latitude, longitude, place.latitude, place.longitude) * 1000.0
        if dist_m <= place.radius_m:
            if best is None or dist_m < best[1]:
                best = (place, dist_m)
    return best


def reverse_geocode_label(latitude: float, longitude: float) -> str:
    params = parse.urlencode(
        {
            "format": "jsonv2",
            "lat": f"{latitude:.6f}",
            "lon": f"{longitude:.6f}",
            "zoom": "18",
            "addressdetails": "1",
        }
    )
    payload = fetch_public_json(f"https://nominatim.openstreetmap.org/reverse?{params}")
    address = payload.get("address") if isinstance(payload, dict) else None
    if not isinstance(address, dict):
        return ""

    parts: list[str] = []
    road = address.get("road")
    neighbourhood = (
        address.get("neighbourhood")
        or address.get("suburb")
        or address.get("quarter")
        or address.get("city_district")
    )
    city = address.get("city") or address.get("town") or address.get("village")

    if road:
        parts.append(str(road))
    if neighbourhood and neighbourhood not in parts:
        parts.append(str(neighbourhood))
    if city and city not in parts:
        parts.append(str(city))
    return ", ".join(parts[:3])


def distance_meters(a: Position, b: Position) -> float:
    return haversine_km(a, b) * 1000.0


def representative_position(points: list[Position]) -> Position:
    return points[len(points) // 2]


def candidate_stop_window(points: list[Position]) -> StopWindow | None:
    if not points:
        return None
    start = points[0]
    end = points[-1]
    dwell_minutes = (end.timestamp - start.timestamp).total_seconds() / 60.0
    if dwell_minutes < MIN_STOP_MINUTES:
        return None
    return StopWindow(start=start, end=end, points=points)


def detect_stationary_stops(positions: list[Position]) -> list[StopWindow]:
    stops: list[StopWindow] = []
    current: list[Position] = []
    anchor: Position | None = None

    for pos in positions:
        if pos.speed_kph > STATIONARY_SPEED_KPH:
            stop = candidate_stop_window(current)
            if stop is not None:
                stops.append(stop)
            current = []
            anchor = None
            continue

        if not current:
            current = [pos]
            anchor = pos
            continue

        assert anchor is not None
        if distance_meters(anchor, pos) <= STOP_RADIUS_M:
            current.append(pos)
            continue

        stop = candidate_stop_window(current)
        if stop is not None:
            stops.append(stop)
        current = [pos]
        anchor = pos

    stop = candidate_stop_window(current)
    if stop is not None:
        stops.append(stop)
    return stops


def summarize_stop_clusters(positions: list[Position], places: list[SavedPlace]) -> list[str]:
    summaries: list[str] = []
    for stop in detect_stationary_stops(positions):
        anchor = representative_position(stop.points)
        saved = nearest_saved_place(anchor, places)
        address = next((p.address for p in stop.points if p.address), "")
        if saved is not None:
            label = saved[0].name
        elif address:
            label = address
        else:
            label = f"{anchor.latitude:.4f}, {anchor.longitude:.4f}"
        summaries.append(
            f"{stop.start.timestamp.strftime('%H:%M')}-{stop.end.timestamp.strftime('%H:%M')} | {label}"
        )
    return summaries[:8]


def summarize_report_stops(stops: list[ReportStop], places: list[SavedPlace]) -> list[str]:
    summaries: list[str] = []
    for stop in stops:
        dwell_minutes = (stop.end - stop.start).total_seconds() / 60.0
        if dwell_minutes < MIN_STOP_MINUTES:
            continue
        saved = nearest_saved_place_for_coords(stop.latitude, stop.longitude, places)
        if saved is not None:
            label = saved[0].name
        elif stop.address:
            label = stop.address
        else:
            label = reverse_geocode_label(stop.latitude, stop.longitude) or f"{stop.latitude:.4f}, {stop.longitude:.4f}"
        summaries.append(
            f"{stop.start.strftime('%H:%M')}-{stop.end.strftime('%H:%M')} | {label}"
        )
    return summaries[:8]


def print_summary(
    day_text: str,
    positions: list[Position],
    places: list[SavedPlace],
    source_label: str,
    config: TraccarConfig | None = None,
) -> None:
    print(f"Location context for {day_text}:")
    if not positions:
        print(f"- No {source_label} positions found for this date.")
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
    print(f"- Source: {source_label}")
    print(f"- Position samples: {len(positions)}")
    print(f"- First seen: {first.timestamp.strftime('%H:%M')} | {first.latitude:.4f}, {first.longitude:.4f}")
    print(f"- Last seen: {last.timestamp.strftime('%H:%M')} | {last.latitude:.4f}, {last.longitude:.4f}")
    if current_place is not None:
        print(f"- Current place label: {current_place[0].name} ({current_place[1]:.0f} m from saved point)")
    print(f"- Approx travel distance: {total_distance_km:.1f} km")
    print(f"- Moving samples: {moving_points}")
    print(f"- Peak observed speed: {max_speed:.1f} km/h")

    stops: list[str] = []
    if config is not None:
        try:
            report_stops = fetch_report_stops(config, day_text)
            stops = summarize_report_stops(report_stops, places)
        except Exception:
            stops = []

    if not stops:
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

    places = load_places(PLACES_FILE)
    owntracks_s3_config = build_owntracks_s3_config()
    if owntracks_s3_config is not None:
        try:
            owntracks_positions = fetch_owntracks_s3_positions(owntracks_s3_config, args.date)
        except Exception:
            owntracks_positions = []
        if owntracks_positions:
            print_summary(args.date, owntracks_positions, places, "OwnTracks/S3")
            return 0

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

    print_summary(args.date, positions, places, "Traccar", config=config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
