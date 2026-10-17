
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml


# Locate config/watches.yaml relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "watches.yaml"


def load_watches(config_path=DEFAULT_CONFIG):
    """Load and validate the basic structure of the watches config."""

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping.")

    watches = config.get("watches")

    if not isinstance(watches, list) or not watches:
        raise ValueError("'watches' must be a non-empty list.")

    names = set()

    for watch in watches:
        if not isinstance(watch, dict):
            raise ValueError("Each watch must be a mapping.")

        name = watch.get("name")
        kind = watch.get("kind")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every watch needs a non-empty name.")

        if name in names:
            raise ValueError(f"Duplicate watch name: {name}")

        names.add(name)

        if kind not in ("closed", "rolling"):
            raise ValueError(
                f"Watch '{name}' has an unsupported kind: {kind}"
            )

        try:
            magnitude = float(watch["minmagnitude"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"Watch '{name}' needs a numeric minmagnitude."
            ) from error

        if not -2 <= magnitude <= 10:
            raise ValueError(
                f"Watch '{name}' has an invalid minmagnitude."
            )

        if kind == "closed":
            try:
                start = date.fromisoformat(watch["starttime"])
                end = date.fromisoformat(watch["endtime"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Watch '{name}' needs valid ISO dates."
                ) from error

            if end <= start:
                raise ValueError(
                    f"Watch '{name}': endtime must follow starttime."
                )

        else:
            days = watch.get("days")

            if type(days) is not int or days <= 0:
                raise ValueError(
                    f"Watch '{name}' needs a positive integer 'days'."
                )

    return watches


def build_query(watch, now=None, limit=100, offset=1):
    """Convert one watch into USGS API query parameters."""

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("'now' must be timezone-aware.")

    now = now.astimezone(timezone.utc)

    if limit < 1 or offset < 1:
        raise ValueError("limit and offset must be positive.")

    query = {
        "format": "geojson",
        "limit": limit,
        "offset": offset,
        "orderby": "time",
        "minmagnitude": float(watch["minmagnitude"]),
    }

    if watch["kind"] == "closed":
        start = date.fromisoformat(watch["starttime"])
        end = date.fromisoformat(watch["endtime"])

        if end <= start:
            raise ValueError("endtime must follow starttime.")

        query["starttime"] = start.isoformat()
        query["endtime"] = end.isoformat()

    elif watch["kind"] == "rolling":
        days = watch["days"]

        if type(days) is not int or days <= 0:
            raise ValueError("'days' must be a positive integer.")

        start = now - timedelta(days=days)

        query["starttime"] = start.strftime("%Y-%m-%dT%H:%M:%S")
        query["endtime"] = now.strftime("%Y-%m-%dT%H:%M:%S")

    else:
        raise ValueError(f"Unsupported watch kind: {watch['kind']}")

    return query
