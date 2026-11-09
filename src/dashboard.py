import json
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from watcher.db import get_connection


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Open Data Change Detector",
    page_icon="🌍",
    layout="wide",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* Main page */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background-color: #242424;
        border: 1px solid #333333;
        border-radius: 14px;
        padding: 20px;
        min-height: 150px;
    }

    div[data-testid="stMetricLabel"] {
        color: #a8a8a8;
        font-size: 15px;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #f5f5f5;
        font-size: 24px;
    }

    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        white-space: pre-line !important;
        overflow: visible !important;
        text-overflow: clip !important;
        line-height: 1.3;
    }

    /* Alert cards */
    .alert-card {
        background-color: #242424;
        border: 1px solid #333333;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }

    .alert-title {
        font-size: 18px;
        font-weight: 600;
        color: #f5f5f5;
        margin-bottom: 8px;
    }

    .alert-time {
        color: #999999;
        font-size: 13px;
        margin-bottom: 10px;
    }

    .alert-details {
        color: #c8c8c8;
        font-size: 13px;
        line-height: 1.5;
    }

    /* Section spacing */
    .section-title {
        font-size: 25px;
        font-weight: 700;
        margin-top: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TITLE
# ============================================================

st.title("🌍 Open Data Change Detector")

st.caption(
    "USGS Earthquake Dataset Monitoring Dashboard"
)


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def query_dataframe(query, params=None):
    """
    Execute a SELECT query and return the result as a DataFrame.
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(query, params)

            rows = cur.fetchall()

            if cur.description is None:
                return pd.DataFrame()

            columns = [
                description.name
                for description in cur.description
            ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def load_watches():
    """
    Load all registered watches.
    """

    return query_dataframe(
        """
        SELECT
            id,
            name,
            config
        FROM watches
        ORDER BY name;
        """
    )


def load_snapshots(watch_id):
    """
    Load snapshots for one watch.
    """

    return query_dataframe(
        """
        SELECT
            id,
            watch_id,
            fetched_at,
            status,
            event_count,
            fetch_ms,
            newest_event_ms
        FROM snapshots
        WHERE watch_id = %s
        ORDER BY fetched_at DESC;
        """,
        (watch_id,),
    )


def load_alerts(watch_id):
    """
    Load recent alerts for one watch.
    """

    return query_dataframe(
        """
        SELECT
            id,
            watch_id,
            created_at,
            alert_type,
            details
        FROM alerts
        WHERE watch_id = %s
        ORDER BY created_at DESC
        LIMIT 100;
        """,
        (watch_id,),
    )


def load_snapshot_events(snapshot_id):
    """
    Load all events belonging to one snapshot.
    """

    return query_dataframe(
        """
        SELECT
            event_id,
            event_hash,
            event_data
        FROM snapshot_events
        WHERE snapshot_id = %s
        ORDER BY event_id;
        """,
        (snapshot_id,),
    )


# ============================================================
# JSON HELPERS
# ============================================================

def parse_json(value):
    """
    Safely convert PostgreSQL JSON/JSONB/string data into a dict.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):

        try:
            result = json.loads(value)

            if isinstance(result, dict):
                return result

            return {}

        except Exception:
            return {}

    return {}


def parse_event_data(event_data):
    """
    Parse event_data stored in snapshot_events.
    """

    return parse_json(event_data)


# ============================================================
# EVENT COORDINATES
# ============================================================

def extract_coordinates(event_data):
    """
    Extract longitude, latitude and depth from USGS GeoJSON.

    Standard structure:

        geometry:
            coordinates:
                [longitude, latitude, depth]
    """

    geometry = event_data.get(
        "geometry",
        {},
    )

    coordinates = geometry.get(
        "coordinates",
        [],
    )

    if (
        isinstance(coordinates, (list, tuple))
        and len(coordinates) >= 2
    ):

        try:

            longitude = float(
                coordinates[0]
            )

            latitude = float(
                coordinates[1]
            )

            depth = None

            if len(coordinates) >= 3:

                try:

                    depth = float(
                        coordinates[2]
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    depth = None

            if (
                -180 <= longitude <= 180
                and -90 <= latitude <= 90
            ):

                return (
                    longitude,
                    latitude,
                    depth,
                )

        except (
            TypeError,
            ValueError,
        ):

            pass

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    properties = event_data.get(
        "properties",
        {},
    )

    longitude = properties.get(
        "longitude"
    )

    latitude = properties.get(
        "latitude"
    )

    if (
        longitude is not None
        and latitude is not None
    ):

        try:

            longitude = float(
                longitude
            )

            latitude = float(
                latitude
            )

            if (
                -180 <= longitude <= 180
                and -90 <= latitude <= 90
            ):

                return (
                    longitude,
                    latitude,
                    None,
                )

        except (
            TypeError,
            ValueError,
        ):

            pass

    return None


# ============================================================
# EVENT INFORMATION
# ============================================================

def extract_event_information(
    event_id,
    event_data,
):
    """
    Extract useful earthquake information.
    """

    properties = event_data.get(
        "properties",
        {},
    )

    coordinates = extract_coordinates(
        event_data
    )

    if coordinates is None:
        return None

    (
        longitude,
        latitude,
        depth,
    ) = coordinates

    magnitude = properties.get(
        "mag"
    )

    if magnitude is None:
        magnitude = 0

    try:

        magnitude = float(
            magnitude
        )

    except (
        TypeError,
        ValueError,
    ):

        magnitude = 0

    return {
        "event_id": event_id,
        "longitude": longitude,
        "latitude": latitude,
        "depth_km": depth,
        "magnitude": magnitude,
        "place": properties.get(
            "place",
            "Unknown",
        ),
        "time": properties.get(
            "time"
        ),
        "status": properties.get(
            "status",
            "unknown",
        ),
        "url": properties.get(
            "url"
        ),
    }


# ============================================================
# TIME HELPERS
# ============================================================

def format_ist_datetime(value):
    """
    Convert a timestamp to IST.
    """

    try:

        timestamp = pd.to_datetime(
            value,
            utc=True,
        )

        timestamp = timestamp.tz_convert(
            "Asia/Kolkata"
        )

        return timestamp.strftime(
            "%d %b %Y, %H:%M:%S IST"
        )

    except Exception:

        return "Unknown"


def format_event_age(event_ms):
    """
    Convert USGS milliseconds since epoch
    into a human-readable age.
    """

    if pd.isna(event_ms):
        return "Unknown"

    try:

        event_time = datetime.fromtimestamp(
            float(event_ms) / 1000,
            tz=timezone.utc,
        )

        now = datetime.now(
            timezone.utc
        )

        age_seconds = (
            now - event_time
        ).total_seconds()

        if age_seconds < 0:
            return "Just now"

        if age_seconds < 60:
            return (
                f"{int(age_seconds)} sec ago"
            )

        if age_seconds < 3600:
            return (
                f"{int(age_seconds / 60)} min ago"
            )

        if age_seconds < 86400:
            return (
                f"{int(age_seconds / 3600)} hr ago"
            )

        return (
            f"{int(age_seconds / 86400)} days ago"
        )

    except Exception:

        return "Unknown"


# ============================================================
# ALERT HELPERS
# ============================================================

def alert_icon(alert_type):
    """
    Return an icon for an alert type.
    """

    if alert_type == "EVENTS_ADDED":
        return "🟢"

    if alert_type == "EVENTS_REMOVED":
        return "🔴"

    if alert_type == "EVENTS_REVISED":
        return "🟠"

    if "ROW_COUNT" in str(alert_type):
        return "🟡"

    if alert_type == "SCHEMA_CHANGED":
        return "🔵"

    if alert_type == "CONTENT_CHANGED":
        return "🟣"

    if "FETCH" in str(alert_type):
        return "⚠️"

    return "⚪"


def format_alert_details(details):
    """
    Convert alert JSON into readable text.

    This intentionally avoids dumping huge JSON blobs
    into the dashboard.
    """

    details = parse_json(details)

    if not details:
        return ""

    parts = []

    if "count" in details:
        parts.append(
            f"Count: {details['count']}"
        )

    if "event_count" in details:
        parts.append(
            f"Event count: {details['event_count']}"
        )

    if "old_count" in details:
        parts.append(
            f"Previous count: {details['old_count']}"
        )

    if "new_count" in details:
        parts.append(
            f"Current count: {details['new_count']}"
        )

    if "old_hash" in details:
        parts.append(
            f"Previous hash: {details['old_hash']}"
        )

    if "new_hash" in details:
        parts.append(
            f"Current hash: {details['new_hash']}"
        )

    events = details.get(
        "events",
        [],
    )

    if events:

        event_ids = []

        for event in events[:5]:

            event_id = event.get(
                "event_id"
            )

            if event_id:
                event_ids.append(
                    event_id
                )

        if event_ids:

            parts.append(
                "Events: "
                + ", ".join(event_ids)
            )

    return " • ".join(parts)


# ============================================================
# WATCH SELECTOR
# ============================================================

try:

    watches = load_watches()

except Exception as error:

    st.error(
        "Could not connect to PostgreSQL."
    )

    st.code(
        str(error)
    )

    st.info(
        "Check your .env PostgreSQL credentials "
        "and make sure the Docker PostgreSQL container "
        "is running."
    )

    st.stop()


if watches.empty:

    st.warning(
        "No watches have been registered yet."
    )

    st.stop()


watch_options = {}

for _, row in watches.iterrows():

    name = str(
        row["name"]
    )

    watch_id = int(
        row["id"]
    )

    config = parse_json(
        row["config"]
    )

    if name == "rolling-7d":

        label = (
            "Rolling 7 Days — M2.5+"
        )

    elif name == "live":

        label = (
            "Live Feed — All Magnitudes"
        )

    else:

        label = name

    watch_options[label] = watch_id


selected_watch = st.selectbox(
    "Select Watch",
    list(watch_options.keys()),
)


watch_id = watch_options[
    selected_watch
]


# ============================================================
# WATCH DESCRIPTION
# ============================================================

if "Rolling 7 Days" in selected_watch:

    st.caption(
        "Rolling 7 Days — M2.5+ · "
        "Earthquakes from the last 7 days "
        "with magnitude ≥ 2.5"
    )

elif "Live Feed" in selected_watch:

    st.caption(
        "Live Feed — All Magnitudes · "
        "USGS real-time earthquake feed — "
        "all reported magnitudes"
    )

else:

    st.caption(
        f"Monitoring watch: {selected_watch}"
    )


# ============================================================
# LIVE DASHBOARD
# ============================================================

@st.fragment(run_every="30s")
def live_dashboard():

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    try:

        snapshots = load_snapshots(
            watch_id
        )

        alerts = load_alerts(
            watch_id
        )

    except Exception as error:

        st.error(
            "Could not load dashboard data "
            "from PostgreSQL."
        )

        st.code(
            str(error)
        )

        return


    if snapshots.empty:

        st.warning(
            "No snapshots have been recorded "
            "for this watch yet."
        )

        return


    latest = snapshots.iloc[0]


    # ========================================================
    # TOP METRICS
    # ========================================================

    last_check = format_ist_datetime(
        latest["fetched_at"]
    ).replace(", ", "\n")

    newest_event = format_event_age(
        latest["newest_event_ms"]
    )

    event_count = int(
        latest["event_count"]
    )

    recent_alert_count = len(
        alerts
    )


    col1, col2, col3, col4 = st.columns(
        4
    )


    with col1:

        st.metric(
            label="LAST CHECK",
            value=last_check,
        )

        st.caption(
            "Most recent successful check"
        )


    with col2:

        st.metric(
            label="NEWEST EVENT",
            value=newest_event,
        )

        st.caption(
            "Age of the newest earthquake"
        )


    with col3:

        st.metric(
            label="EVENTS TRACKED",
            value=event_count,
        )

        st.caption(
            "Events in the latest snapshot"
        )


    with col4:

        st.metric(
            label="RECENT ALERTS",
            value=recent_alert_count,
        )

        st.caption(
            "Alerts retained for this watch"
        )


    # ========================================================
    # EVENT COUNT OVER TIME
    # ========================================================

    st.divider()

    st.subheader(
        "📈 Event Count Over Time"
    )

    chart_data = snapshots[["fetched_at", "event_count"]].copy()

    chart_data["fetched_at"] = (
        pd.to_datetime(chart_data["fetched_at"], utc=True)
        .dt.tz_convert("Asia/Kolkata")
        .dt.tz_localize(None)
    )

    chart_data["event_count"] = pd.to_numeric(
        chart_data["event_count"],
        errors="coerce",
    )

    chart_data = (
        chart_data
        .dropna()
        .sort_values("fetched_at")
    )

    chart = (
        alt.Chart(chart_data)
        .mark_line()
        .encode(
            x=alt.X(
                "fetched_at:T",
                title="Time (IST)",
                axis=alt.Axis(
                    format="%d %b, %H:%M",
                    labelAngle=-45,
                    tickCount=8,
                ),
            ),
            y=alt.Y("event_count:Q", title="Events"),
            tooltip=[
                alt.Tooltip(
                    "fetched_at:T",
                    title="Checked at (IST)",
                    format="%d %b %Y, %H:%M:%S",
                ),
                alt.Tooltip("event_count:Q", title="Events"),
            ],
        )
        .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)


    # ========================================================
    # LATEST SNAPSHOT EVENTS
    # ========================================================

    try:

        events = load_snapshot_events(
            int(latest["id"])
        )

    except Exception as error:

        st.error(
            "Could not load snapshot events."
        )

        st.code(
            str(error)
        )

        return


    # ========================================================
    # BUILD MAP DATA
    # ========================================================

    st.divider()

    st.subheader(
        "🌍 Earthquake Map"
    )

    map_rows = []


    for _, row in events.iterrows():

        event_data = parse_event_data(
            row["event_data"]
        )

        information = (
            extract_event_information(
                row["event_id"],
                event_data,
            )
        )

        if information is not None:

            map_rows.append(
                information
            )


    map_df = pd.DataFrame(
        map_rows
    )


    # ========================================================
    # FIND REVISED EVENTS
    # ========================================================

    revised_event_ids = set()


    for _, alert in alerts.iterrows():

        if (
            alert["alert_type"]
            != "EVENTS_REVISED"
        ):
            continue


        details = parse_json(
            alert["details"]
        )


        for event in details.get(
            "events",
            [],
        ):

            event_id = event.get(
                "event_id"
            )

            if event_id:

                revised_event_ids.add(
                    event_id
                )


    # ========================================================
    # SHOW MAP
    # ========================================================

    if map_df.empty:

        st.warning(
            "No valid earthquake coordinates "
            "were found in the latest snapshot."
        )

        st.info(
            f"{len(events)} stored events were checked. "
            "The map expects USGS GeoJSON coordinates "
            "in geometry.coordinates as "
            "[longitude, latitude, depth]."
        )

    else:

        map_df["revised"] = (
            map_df["event_id"]
            .isin(
                revised_event_ids
            )
        )


        # ----------------------------------------------------
        # MARKER SIZE
        # ----------------------------------------------------

        map_df["radius"] = (
            map_df["magnitude"]
            .clip(
                lower=0.1
            )
            * 60000
        ).clip(
            lower=250000
        )


        normal_df = map_df[
            ~map_df["revised"]
        ].copy()


        revised_df = map_df[
            map_df["revised"]
        ].copy()


        revised_df["radius"] = (
            revised_df["magnitude"]
            .clip(
                lower=0.1
            )
            * 70000
        ).clip(
            lower=350000
        )


        # ----------------------------------------------------
        # MAP LAYERS
        # ----------------------------------------------------

        layers = []


        if not normal_df.empty:

            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=normal_df,
                    get_position=[
                        "longitude",
                        "latitude",
                    ],
                    get_radius="radius",
                    get_fill_color=[
                        150,
                        150,
                        150,
                        190,
                    ],
                    pickable=True,
                    stroked=True,
                    get_line_color=[
                        255,
                        255,
                        255,
                        120,
                    ],
                    get_line_width=1,
                )
            )


        if not revised_df.empty:

            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=revised_df,
                    get_position=[
                        "longitude",
                        "latitude",
                    ],
                    get_radius="radius",
                    get_fill_color=[
                        255,
                        140,
                        0,
                        220,
                    ],
                    pickable=True,
                    stroked=True,
                    get_line_color=[
                        255,
                        255,
                        255,
                        180,
                    ],
                    get_line_width=1,
                )
            )


        # ----------------------------------------------------
        # MAP VIEW
        # ----------------------------------------------------

        view_state = pdk.ViewState(
            latitude=20,
            longitude=0,
            zoom=1.0,
        )


        deck = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            map_style=None,
            tooltip={
                "html": """
                    <b>Event:</b> {event_id}<br/>
                    <b>Magnitude:</b> {magnitude}<br/>
                    <b>Location:</b> {place}<br/>
                    <b>Latitude:</b> {latitude}<br/>
                    <b>Longitude:</b> {longitude}<br/>
                    <b>Depth:</b> {depth_km} km<br/>
                    <b>Status:</b> {status}
                """
            },
        )


        st.pydeck_chart(
            deck,
            use_container_width=True,
        )


        st.caption(
            f"Showing {len(map_df)} earthquake events. "
            "Gray = normal | Orange = revised. "
            "Marker size is based on magnitude."
        )


        # ----------------------------------------------------
        # COORDINATE TABLE
        # ----------------------------------------------------

        with st.expander(
            "📍 View earthquake coordinates"
        ):

            coordinate_columns = [
                "event_id",
                "latitude",
                "longitude",
                "depth_km",
                "magnitude",
                "place",
                "status",
            ]

            coordinate_df = map_df[
                coordinate_columns
            ].copy()


            st.dataframe(
                coordinate_df,
                use_container_width=True,
                hide_index=True,
            )


    # ========================================================
    # EVENTS PER DAY
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Events Per Day"
    )

    daily_rows = []


    for _, row in events.iterrows():

        event_data = parse_event_data(
            row["event_data"]
        )

        properties = event_data.get(
            "properties",
            {}
        )

        event_time = properties.get(
            "time"
        )

        if event_time is None:
            continue


        try:

            event_datetime = pd.to_datetime(
                event_time,
                unit="ms",
                utc=True,
            ).tz_convert(
                "Asia/Kolkata"
            )

            daily_rows.append(
                event_datetime.date()
            )

        except Exception:

            continue


    if daily_rows:

        daily_counts = (
            pd.Series(
                daily_rows
            )
            .value_counts()
            .sort_index()
        )


        daily_counts.index = pd.to_datetime(
            daily_counts.index
        )


        daily_counts.name = (
            "Events"
        )


        st.bar_chart(
            daily_counts,
            use_container_width=True,
        )

    else:

        st.info(
            "No event timestamps available."
        )


    # ========================================================
    # RECENT ALERTS
    # ========================================================

    st.divider()

    st.subheader(
        "🚨 Recent Alerts"
    )

    if alerts.empty:

        st.info(
            "No alerts have been generated."
        )

    else:

        for _, alert in (
            alerts.head(10)
            .iterrows()
        ):

            alert_type = str(
                alert["alert_type"]
            )

            icon = alert_icon(
                alert_type
            )

            created_at = format_ist_datetime(
                alert["created_at"]
            )

            details_text = format_alert_details(
                alert["details"]
            )


            # ------------------------------------------------
            # IMPORTANT:
            # Use native Streamlit containers instead
            # of raw HTML alert blocks.
            # This prevents <div>, <br>, &nbsp;, etc.
            # from appearing as text.
            # ------------------------------------------------

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### {icon} {alert_type}"
                )

                st.caption(
                    created_at
                )

                if details_text:

                    st.write(
                        details_text
                    )


    # ========================================================
    # REVISED EVENTS
    # ========================================================

    st.divider()

    st.subheader(
        "🟠 Revised Events"
    )

    revised_rows = []


    for _, alert in alerts.iterrows():

        if (
            alert["alert_type"]
            != "EVENTS_REVISED"
        ):
            continue


        details = parse_json(
            alert["details"]
        )


        for event in details.get(
            "events",
            [],
        ):

            event_id = event.get(
                "event_id",
                "Unknown",
            )


            for change in event.get(
                "changed_fields",
                [],
            ):

                revised_rows.append(
                    {
                        "Event ID":
                            event_id,

                        "Field":
                            change.get(
                                "field"
                            ),

                        "Before":
                            change.get(
                                "old_value"
                            ),

                        "After":
                            change.get(
                                "new_value"
                            ),
                    }
                )


    if revised_rows:

        revised_df = pd.DataFrame(
            revised_rows
        )

        st.dataframe(
            revised_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No revised events have "
            "been detected yet."
        )


    # ========================================================
    # DASHBOARD STATUS
    # ========================================================

    st.divider()

    st.caption(
        "🔄 Dashboard automatically refreshes "
        "every 30 seconds."
    )

    st.caption(
        "Data source: USGS Earthquake Hazards Program"
    )


# ============================================================
# START DASHBOARD
# ============================================================

live_dashboard()