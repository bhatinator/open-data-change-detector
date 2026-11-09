# 🌍 Open Data Change Detector

### Automated monitoring, change detection, PostgreSQL persistence, Discord alerts, and a Streamlit dashboard for live and historical open-data sources.


<p align="center">
  <strong>
    📊 Real-time Monitoring
    •
    🔍 Change Detection
    •
    🗄️ PostgreSQL
    •
    🚨 Discord Alerts
    •
    🌎 Streamlit Dashboard
  </strong>
</p>

<p align="center">
  <a href="https://discord.gg/BGZ4KUmav">
    <strong>💬 Join the Discord Community</strong>
  </a>
</p>

---

## 🎬 Project Demo

<p align="center">
  <a href="docs/demo/dashboard-demo.mp4">
    <img src="docs/screenshots/dashboard-live.png"
         alt="Open Data Change Detector Demo"
         width="1000">
  </a>
</p>

<p align="center">
  ▶️ <strong>Click the dashboard preview above to watch the full MP4 demonstration.</strong>
</p>

---

## 📸 Dashboard Preview

<p align="center">
  <img src="docs/screenshots/dashboard-live.png"
       alt="Live Monitoring Dashboard"
       width="48%">
  <img src="docs/screenshots/dashboard-map.png"
       alt="Earthquake Map"
       width="48%">
</p>

<p align="center">
  <img src="docs/screenshots/dashboard-events.png"
       alt="Events Per Day Chart"
       width="48%">
  <img src="docs/screenshots/dashboard-alerts.png"
       alt="Recent Alerts Dashboard"
       width="48%">
</p>

---

# 🚀 Overview

**Open Data Change Detector** is a Python-based data monitoring and observability system designed to continuously watch open datasets and identify meaningful changes between successive data snapshots.

The project currently uses the **USGS Earthquake API** and the **USGS real-time earthquake feed** as its primary data sources.

Instead of simply downloading the latest dataset, the system maintains historical snapshots and compares the current state of the data against previous runs.

This allows it to identify changes such as:

- ➕ New records
- ➖ Removed records
- ✏️ Revised records
- 🔄 Silent content changes
- 📊 Significant row-count changes
- 🧱 Schema changes
- ⚠️ Fetch failures
- 🕐 Unexpected data behavior
- 🐌 Slow data retrieval

Detected changes are persisted in **PostgreSQL**, displayed through an interactive **Streamlit dashboard**, and can be delivered through **Discord notifications**.

---

# 🎯 Problem Statement

External datasets and APIs are not always stable.

A dataset that works correctly today may behave differently tomorrow.

For example:

```text
Yesterday:
304 earthquake records

Today:
307 earthquake records
```

That could simply mean that three new earthquakes occurred.

However, other situations may be more difficult to detect:

```text
Yesterday:
304 records

Today:
304 records
```

The row count is identical, but an existing earthquake may have been modified.

For example:

```text
Magnitude:
5.1 → 5.4
```

or:

```text
Location:
California → Southern California
```

A basic row-count check would miss this.

The purpose of this project is therefore to create a monitoring layer capable of detecting both **obvious and subtle dataset changes**.

---

# 💡 Core Idea

The system follows a simple principle:

> **Every dataset fetch becomes a snapshot, every snapshot receives a fingerprint, and every new fingerprint is compared against the previous state.**

Conceptually:

```text
Fetch
  ↓
Validate
  ↓
Fingerprint
  ↓
Compare
  ↓
Classify Changes
  ↓
Persist
  ↓
Alert
  ↓
Visualize
```

---

# 🏗️ System Architecture

```mermaid
flowchart TD

    A[USGS Earthquake Data] --> B{Data Source}

    B --> C[Historical API<br/>Rolling 7 Days]
    B --> D[Real-Time Feed<br/>Latest Hour]

    C --> E[Python Fetcher]
    D --> E

    E --> F[Data Validation]

    F --> G[Fingerprint Engine]

    G --> H[Change Detection Engine]

    H --> I[(PostgreSQL)]

    H --> J[Alert Generation]

    J --> K[Notification Outbox]

    K --> L[Discord Webhook]

    I --> M[Streamlit Dashboard]

    M --> N[Charts]
    M --> O[Earthquake Map]
    M --> P[Snapshot History]
    M --> Q[Recent Alerts]
```

---

# 🔄 End-to-End Workflow

```mermaid
flowchart LR

    A[External Dataset] --> B[Fetch Data]

    B --> C[Validate Response]

    C --> D[Create Fingerprint]

    D --> E[Load Previous Snapshot]

    E --> F[Compare Current vs Previous]

    F --> G{Change Detected?}

    G -->|No| H[Store Snapshot]

    G -->|Yes| I[Classify Change]

    I --> J[Added Events]
    I --> K[Removed Events]
    I --> L[Revised Events]
    I --> M[Content Changes]
    I --> N[Count Changes]

    J --> O[Generate Alert]
    K --> O
    L --> O
    M --> O
    N --> O

    O --> P[(PostgreSQL)]
    O --> Q[Discord]

    P --> R[Streamlit Dashboard]
```

---

# 🔍 Change Detection

The detector performs event-level and dataset-level comparisons.

## ➕ 1. Events Added

If an event exists in the current dataset but was not present in the previous snapshot:

```text
Previous:
304 events

Current:
307 events

Detected:
3 events added
```

The system records the new event IDs.

---

## ➖ 2. Events Removed

If an event existed previously but is missing from the current snapshot:

```text
Previous:
304 events

Current:
301 events

Detected:
3 events removed
```

This can indicate an upstream deletion, correction, or unexpected data change.

---

## ✏️ 3. Events Revised

An event can remain present while one or more of its fields changes.

Example:

```text
Event ID:
abc123

Magnitude:
5.1 → 5.3
```

The event remains in the dataset, but its fingerprint changes.

The detector classifies this as a revision.

---

## 🔄 4. Content Changes

Content changes allow the system to identify silent modifications to existing records.

For example:

```text
Before:
Place = "California"

After:
Place = "Southern California"
```

Even if the total number of records remains unchanged, the system can detect the modification.

---

## 📊 5. Count Changes

The detector also monitors the total number of records.

Example:

```text
Previous count: 304
Current count: 352

Difference: +48
```

Thresholds can be configured to determine whether such a change should generate an alert.

---

## 🧱 6. Schema Changes

A dataset's structure is also part of its fingerprint.

The system can monitor changes involving:

- Added fields
- Removed fields
- Renamed fields
- Changed field types
- Unexpected structural changes

This is particularly important for production data pipelines because an upstream schema change can break downstream processing.

---

# 🧬 Dataset Fingerprinting

Every successful fetch produces a dataset fingerprint.

The fingerprint captures information such as:

```text
Schema
Row Count
Event Hashes
Content Hash
Fetch Status
Fetch Duration
Newest Event Timestamp
```

The general process is:

```mermaid
flowchart TD

    A[Dataset] --> B[Extract Schema]

    A --> C[Count Records]

    A --> D[Extract Event IDs]

    D --> E[Hash Individual Events]

    E --> F[Generate Content Hash]

    A --> G[Collect Fetch Metadata]

    B --> H[Dataset Fingerprint]
    C --> H
    F --> H
    G --> H
```

The resulting fingerprint provides a compact representation of the state of the dataset at a particular point in time.

---

# 🗄️ PostgreSQL Persistence

PostgreSQL acts as the historical state store for the monitoring system.

Instead of keeping only the latest dataset, the system stores:

- Watches
- Snapshots
- Event fingerprints
- Event data
- Event state
- Alerts
- Notification records

This makes it possible to reconstruct what happened over time.

---

# 🧩 Database Design

```mermaid
erDiagram

    WATCHES ||--o{ SNAPSHOTS : contains
    WATCHES ||--o{ EVENT_STATE : tracks
    WATCHES ||--o{ ALERTS : generates

    SNAPSHOTS ||--o{ SNAPSHOT_EVENTS : contains
    ALERTS ||--o{ NOTIFICATION_OUTBOX : queues

    WATCHES {
        int id PK
        text name
        jsonb config
    }

    SNAPSHOTS {
        int id PK
        int watch_id FK
        timestamptz fetched_at
        text status
        int event_count
        jsonb schema_json
        text content_hash
        bigint newest_event_ms
        int fetch_ms
    }

    SNAPSHOT_EVENTS {
        int snapshot_id FK
        text event_id
        text event_hash
        jsonb event_data
    }

    EVENT_STATE {
        int watch_id PK
        text event_id PK
        text event_hash
        timestamptz first_seen
        timestamptz last_seen
        timestamptz last_changed
    }

    ALERTS {
        int id PK
        int watch_id FK
        timestamptz created_at
        text alert_type
        jsonb details
    }

    NOTIFICATION_OUTBOX {
        int id PK
        int alert_id FK
        text status
        timestamptz created_at
    }
```

---

# 👀 Monitoring Watches

The project supports multiple independent monitoring watches.

Currently, the system uses two primary watches.

## 🔵 Rolling 7-Day Watch

The rolling watch queries the historical USGS API for earthquake events occurring during the previous seven days.

```yaml
- name: rolling-7d
  kind: rolling
  days: 7
  minmagnitude: 2.5

  detectors:
    min_count_change: 20
    max_count_change_pct: 50
    alert_on_revision: true
    alert_on_content_change: true
```

This provides a historical monitoring window and is useful for detecting revisions and unexpected changes in recent earthquake records.

---

## 🟢 Live Watch

The live watch uses the USGS real-time feed.

```yaml
- name: live
  kind: live
  minmagnitude: 0

  detectors:
    min_count_change: 1
    max_count_change_pct: 100
    alert_on_revision: true
    alert_on_content_change: true
```

The live watch uses a minimum magnitude of `0` so that valid earthquake events are included regardless of magnitude.

---

# ⚙️ Configuration-Driven Design

One of the project's design goals is to avoid hard-coding monitoring behavior inside the application.

Instead, watches are defined in:

```text
config/watches.yaml
```

This makes it possible to modify:

- Watch names
- Watch type
- Time window
- Magnitude threshold
- Count thresholds
- Revision detection
- Content-change detection

without rewriting the monitoring engine.

---

# 🚨 Alert System

The detector can generate alerts for several conditions.

Typical alert types include:

```text
EVENTS_ADDED
EVENTS_REMOVED
EVENTS_REVISED
CONTENT_CHANGED
COUNT_CHANGED
FETCH_FAILED
```

The alerts contain structured information describing what happened.

For example:

```text
EVENTS_REVISED

Event ID:
abc123

Changed field:
magnitude

Previous value:
5.1

Current value:
5.3
```

This information is persisted in PostgreSQL and displayed in the dashboard.

---

# 💬 Discord Notifications

When an alert is generated, the system can send it through a Discord webhook.

```mermaid
flowchart LR

    A[USGS Data] --> B[Fetcher]

    B --> C[Fingerprint]

    C --> D[Change Detector]

    D -->|Change| E[Alert Generator]

    E --> F[(PostgreSQL)]

    E --> G[Notification Outbox]

    G --> H[Discord Webhook]

    H --> I[Discord Channel]
```

### 💬 Join the Project Discord

If you want to follow the monitoring system, alerts, development, or future improvements, join the project Discord community:

**[Join the Open Data Change Detector Discord Community](https://discord.gg/BGZ4KUmav)**

---

# 📊 Streamlit Dashboard

The project includes an interactive Streamlit dashboard designed to provide a visual monitoring interface.

The dashboard displays:

- 📌 Current dataset information
- 📈 Event-count history
- 🌎 Global earthquake map
- 🚨 Recent alerts
- 🟠 Revised events
- ⏱️ Fetch performance
- 📅 Snapshot history
- 🔎 Watch selection
- 🔄 Automatic refresh

The dashboard dynamically loads registered watches from PostgreSQL.

---

# 🌎 Earthquake Visualization

The dashboard extracts geographic information from USGS GeoJSON records.

The visualization uses:

```text
Longitude
Latitude
Depth
Magnitude
Location
```

This allows monitored earthquake events to be displayed geographically.

---

# 📈 Historical Monitoring

Every monitoring run creates a snapshot.

For example:

```text
Snapshot 1
304 events

        ↓

Snapshot 2
304 events

        ↓

Snapshot 3
305 events
+1 event

        ↓

Snapshot 4
305 events
1 revised event
```

This historical approach makes the system useful not only for detecting changes but also for understanding how the dataset evolves over time.

---

# 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| **Python** | Core monitoring application |
| **Requests** | HTTP/API communication |
| **PyYAML** | Watch configuration |
| **PostgreSQL** | Persistent monitoring state |
| **psycopg** | PostgreSQL connectivity |
| **Docker** | Database containerization |
| **Streamlit** | Interactive dashboard |
| **PyDeck** | Geographic visualization |
| **Pandas** | Data processing |
| **pytest** | Automated testing |
| **Discord Webhooks** | Notifications |
| **Git** | Version control |
| **GitHub** | Source code hosting |
| **USGS API** | Earthquake data source |

---

# 📁 Project Structure

```text
open-data-change-detector/
│
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── config/
│   └── watches.yaml
│
├── fixtures/
│
├── logs/
│
├── sql/
│   └── schema.sql
│
├── src/
│   ├── dashboard.py
│   ├── run_watcher.py
│   │
│   └── watcher/
│       ├── __init__.py
│       ├── fetcher.py
│       ├── fingerprint.py
│       ├── watches.py
│       ├── db.py
│       ├── detectors.py
│       ├── discord_notifier.py
│       └── send_notifications.py
│
├── tests/
│
└── docs/
    ├── screenshots/
    │   ├── dashboard-live.png
    │   ├── dashboard-map.png
    │   ├── dashboard-events.png
    │   └── dashboard-alerts.png
    │
    └── demo/
        └── dashboard-demo.mp4
```

---

# 🐳 PostgreSQL with Docker

The project uses PostgreSQL through Docker.

Start the database:

```bash
docker compose up -d
```

Check the running containers:

```bash
docker ps
```

Stop the database:

```bash
docker compose down
```

The database schema is defined in:

```text
sql/schema.sql
```

---

# ▶️ Running the Project

## 1. Clone the repository

```bash
git clone <your-repository-url>
cd open-data-change-detector
```

## 2. Create and activate a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Create:

```text
.env
```

Example:

```env
DATABASE_URL=postgresql://watcher:password@localhost:5432/dataset_watcher
DISCORD_WEBHOOK_URL=your_webhook_url
```

Never commit the real `.env` file.

---

# 🐘 Start PostgreSQL

```bash
docker compose up -d
```

Verify:

```bash
docker ps
```

---

# ▶️ Run the Watcher

From the project root:

```bash
python src/run_watcher.py
```

The watcher will:

1. Load the configured watches.
2. Fetch the dataset.
3. Validate the response.
4. Generate a fingerprint.
5. Load the previous snapshot.
6. Compare current and previous state.
7. Classify detected changes.
8. Generate alerts.
9. Save the new snapshot.
10. Store event-level information.
11. Send notifications when configured.

---

# 📊 Run the Dashboard

Start Streamlit with:

```bash
streamlit run src/dashboard.py
```

The dashboard will open in your browser.

---

# 🧪 Testing

The project uses `pytest` for automated testing.

Run:

```bash
pytest
```

Tests cover important parts of the monitoring system, including:

- Watch configuration
- Query generation
- Data fetching
- Fingerprinting
- Change detection
- Dataset comparison

---

# 🔐 Environment Variables

Sensitive configuration should be stored in `.env`.

Example:

```env
DATABASE_URL=postgresql://watcher:password@localhost:5432/dataset_watcher
DISCORD_WEBHOOK_URL=your_webhook_url
```

The repository should contain:

```text
.env.example
```

instead of the real `.env`.

### Never commit:

```text
.env
```

or real Discord webhook URLs, database passwords, API credentials, or other secrets.

---

# 🌐 Data Source

The project currently uses the **USGS Earthquake Hazards Program**.

Two types of data access are used.

### Historical Earthquake API

Used by the rolling seven-day watch.

```text
USGS FDSN Event API
```

### Real-Time Earthquake Feed

Used by the live watch.

```text
USGS all_hour.geojson
```

The architecture is intentionally designed so additional open-data sources can be integrated later.

---

# 🧠 Data Engineering Concepts Demonstrated

This project brings together several practical data engineering concepts.

### 1. API Data Ingestion

The system retrieves structured data from external APIs and feeds.

### 2. Data Validation

Incoming responses are checked before being processed.

### 3. Data Fingerprinting

Dataset state is represented through hashes and metadata.

### 4. Change Detection

Current data is compared against historical state.

### 5. Event-Level State Tracking

Individual records are tracked across multiple snapshots.

### 6. Database Persistence

Monitoring state is persisted using PostgreSQL.

### 7. Alerting

Unexpected changes can trigger structured alerts.

### 8. Observability

The system records:

```text
Fetch status
Fetch duration
Event counts
Snapshot history
Content changes
Alerts
```

### 9. Data Visualization

The Streamlit dashboard provides a visual interface for monitoring the system.

### 10. Containerization

PostgreSQL is deployed locally through Docker.

---

# 🔬 Example Detection Scenario

Suppose the system records:

```text
Previous Snapshot

Events: 304
```

The next run returns:

```text
Current Snapshot

Events: 305
```

The detector discovers:

```text
+1 new event
```

It then stores:

```text
New event ID
Event fingerprint
Event data
Snapshot ID
Alert
```

If the new event crosses the configured threshold, a notification can be generated.

---

# 🔄 Example Revision Scenario

Suppose:

```text
Previous:

Event ID: abc123
Magnitude: 4.8
```

The next fetch returns:

```text
Current:

Event ID: abc123
Magnitude: 5.0
```

The event ID is unchanged, but the event fingerprint changes.

The detector therefore identifies:

```text
EVENTS_REVISED
```

and records the changed field:

```text
magnitude

Before:
4.8

After:
5.0
```

This is one of the key differences between this project and a simple row-count monitoring script.

---

# 📸 Dashboard Screenshots

## Live Monitoring

![Live Monitoring Dashboard](docs/screenshots/dashboard-live.png)

## Earthquake Map

![Earthquake Map](docs/screenshots/dashboard-map.png)

## Events Per Day

![Events Per Day](docs/screenshots/dashboard-events.png)

## Recent Alerts

![Recent Alerts](docs/screenshots/dashboard-alerts.png)

---

# 🎥 Full Project Demo

The complete dashboard demonstration is available here:

**[▶️ Watch the Full Dashboard Demo](docs/demo/dashboard-demo.mp4)**

---

# 🔮 Future Improvements

The project can be extended significantly.

Potential improvements include:

- [ ] Support for additional open-data APIs
- [ ] Automated schema-drift detection
- [ ] Advanced anomaly detection
- [ ] Email notifications
- [ ] Slack notifications
- [ ] Microsoft Teams notifications
- [ ] Dashboard authentication
- [ ] Cloud deployment
- [ ] Scheduled execution
- [ ] GitHub Actions integration
- [ ] Kubernetes deployment
- [ ] Prometheus metrics
- [ ] Grafana monitoring
- [ ] Dataset health scores
- [ ] Historical anomaly analytics
- [ ] Multi-dataset monitoring
- [ ] Distributed workers
- [ ] Configurable notification routing

---

# ☁️ Potential Production Architecture

The current version is designed for local development using Docker and PostgreSQL.

A production deployment could look like:

```mermaid
flowchart TD

    A[External Open Data APIs] --> B[Scheduled Data Worker]

    B --> C[Data Fetcher]

    C --> D[Fingerprint Engine]

    D --> E[Change Detection]

    E --> F[(Cloud PostgreSQL)]

    E --> G[Alert Service]

    G --> H[Discord]
    G --> I[Email]
    G --> J[Slack]

    F --> K[Streamlit Dashboard]

    K --> L[Cloud Hosting]

    M[Prometheus] --> B
    M --> K

    N[Grafana] --> M
```

This architecture could eventually support monitoring many different datasets simultaneously.

---

# 📈 Why This Project Matters

The project demonstrates an important idea in modern data engineering:

> **Data pipelines should monitor the data they depend on, not simply process it.**

A production pipeline can fail because:

- The API stops responding.
- A dataset unexpectedly shrinks.
- Records disappear.
- Existing records change.
- The schema changes.
- Data becomes stale.
- An upstream provider silently modifies information.

A monitoring layer helps detect these conditions before they propagate into downstream systems.

---

# ⭐ Key Features at a Glance

| Feature | Status |
|---|---|
| USGS historical API | ✅ |
| USGS real-time feed | ✅ |
| Rolling-window monitoring | ✅ |
| Live monitoring | ✅ |
| Dataset fingerprinting | ✅ |
| Event-level hashing | ✅ |
| Added event detection | ✅ |
| Removed event detection | ✅ |
| Revised event detection | ✅ |
| Content-change detection | ✅ |
| Count-change detection | ✅ |
| PostgreSQL persistence | ✅ |
| Docker PostgreSQL | ✅ |
| Streamlit dashboard | ✅ |
| Earthquake map | ✅ |
| Monitoring history | ✅ |
| Discord notifications | ✅ |
| Automated tests | ✅ |

---

# 🤝 Contributing

Contributions, ideas, and improvements are welcome.

Possible areas for contribution include:

- Additional dataset connectors
- New anomaly detectors
- Notification integrations
- Dashboard improvements
- Cloud deployment
- Testing improvements
- Performance optimization

---

# 💬 Community

Have an idea, found an issue, or want to discuss the project?

**[💬 Join the Open Data Change Detector Discord Community](https://discord.gg/BGZ4KUmav)**

---

# 🧑‍💻 Author

## Aryan Bhatia

**Electronics and Computer Engineering**  
**Thapar Institute of Engineering and Technology**

Areas of interest:

- Data Engineering
- Artificial Intelligence
- Machine Learning
- Backend Systems
- Data Infrastructure
- Open Data Systems

---

# 📄 License

This project is licensed under the **MIT License**.

---

<p align="center">

## ⭐ If you found this project interesting, consider giving the repository a star!

**Built with Python • PostgreSQL • Docker • Streamlit • USGS**

</p>