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

**Open Data Change Detector** is a Python-based data monitoring and observability system that continuously watches open datasets and identifies meaningful changes between successive snapshots.

The project currently monitors the **USGS Earthquake API** and **USGS real-time earthquake feed**.

Instead of only checking whether an API is reachable or whether the row count changed, the system maintains historical state and compares the current dataset against previous snapshots. This allows it to detect:

- ➕ New records
- ➖ Removed records
- ✏️ Revised records
- 🔄 Silent content changes
- 📊 Significant row-count changes
- 🧱 Schema changes
- ⚠️ Fetch failures
- 🕐 Unexpected data behaviour
- 🐌 Slow data retrieval

Detected changes are persisted in **PostgreSQL**, displayed through an interactive **Streamlit dashboard**, and can be delivered through **Discord notifications**.

---

# 🎯 Problem Statement

External datasets and APIs are not always stable.

A dataset may return:

```text
Yesterday:
304 records

Today:
307 records
```

That could simply mean three new events were added.

The harder case is:

```text
Yesterday:
304 records

Today:
304 records
```

The row count is unchanged, but an existing record may have been modified:

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

The purpose of this project is therefore to monitor **dataset state**, not just dataset availability.

---

# 💡 Core Idea

> **Every dataset fetch becomes a snapshot, every snapshot receives a fingerprint, and every new fingerprint is compared against the previous state.**

```text
Fetch
  ↓
Validate
  ↓
Fingerprint
  ↓
Compare with Previous State
  ↓
Classify Changes
  ↓
Persist
  ↓
Generate Alerts
  ↓
Notify / Visualize
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

The system is organized around three runtime processes:

| Process | Responsibility |
|---|---|
| **Watcher** — `src/run_watcher.py` | Fetches data, validates it, fingerprints it, compares it with previous state, detects changes, generates alerts, and persists results |
| **Notification Service** — `src/send_notifications.py` | Reads pending records from the PostgreSQL notification outbox and delivers them to Discord |
| **Dashboard** — `src/dashboard.py` | Reads monitoring state from PostgreSQL and presents charts, maps, events, alerts, and history |

This separation keeps **monitoring**, **notification delivery**, and **visualization** independent.

---

# 🔄 Monitoring Workflow

```mermaid
flowchart LR
    A[External Dataset] --> B[Fetch]
    B --> C[Validate]
    C --> D[Fingerprint]
    D --> E[Load Previous Snapshot]
    E --> F[Compare]
    F --> G{Change?}

    G -->|No| H[Store Snapshot]
    G -->|Yes| I[Classify Change]

    I --> J[Added]
    I --> K[Removed]
    I --> L[Revised]
    I --> M[Content Change]
    I --> N[Count Change]

    J --> O[Generate Alert]
    K --> O
    L --> O
    M --> O
    N --> O

    O --> P[(PostgreSQL)]
    O --> Q[Notification Outbox]
    Q --> R[Discord]

    P --> S[Streamlit Dashboard]
```

The watcher performs the complete ingestion-to-persistence workflow. The notification service then handles delivery independently.

---

# 🔍 Change Detection

The detector performs both **event-level** and **dataset-level** comparisons.

### ➕ Events Added

An event exists in the current snapshot but not in the previous snapshot.

```text
Previous: 304 events
Current:  307 events

Detected: 3 events added
```

### ➖ Events Removed

An event existed previously but is missing from the current snapshot.

```text
Previous: 304 events
Current:  301 events

Detected: 3 events removed
```

### ✏️ Events Revised

An event remains present, but its fingerprint changes.

```text
Event ID: abc123

Magnitude:
5.1 → 5.3

→ EVENTS_REVISED
```

### 🔄 Content Changes

Existing records can change without changing the total row count.

```text
Before:
Place = "California"

After:
Place = "Southern California"
```

### 📊 Count Changes

The total number of records is compared against configurable thresholds.

```text
Previous count: 304
Current count: 352

Difference: +48
```

### 🧱 Schema Changes

Schema information is included in the fingerprint so the system can monitor:

- Added fields
- Removed fields
- Renamed fields
- Changed field types
- Other unexpected structural changes

---

# 🧬 Dataset Fingerprinting

Every successful fetch produces a compact representation of the dataset state.

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

This gives the watcher a compact representation of dataset state that can be compared with previous snapshots.

---

# 🗄️ PostgreSQL Persistence

PostgreSQL is the historical state store for the monitoring system.

The database stores:

- Watch configurations
- Dataset snapshots
- Snapshot event records
- Event fingerprints
- Event state
- Alerts
- Notification outbox records

This historical state enables both change detection and monitoring over time.

## Database Design

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

Monitoring behaviour is configured in `config/watches.yaml`.

The project currently uses two primary watches.

## 🔵 Rolling 7-Day Watch

Queries the historical USGS API for earthquake events from the previous seven days.

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

This watch provides a historical monitoring window and is useful for detecting revisions and unexpected changes to recent records.

## 🟢 Live Watch

Uses the USGS real-time earthquake feed.

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

A minimum magnitude of `0` allows valid earthquake events to be included regardless of magnitude.

### Configuration-Driven Design

The YAML configuration controls:

- Watch name
- Watch type
- Time window
- Magnitude threshold
- Count-change thresholds
- Revision detection
- Content-change detection

This allows monitoring behaviour to be changed without modifying the core Python code.

---

# 🚨 Alert System

The detector can generate structured alerts such as:

```text
EVENTS_ADDED
EVENTS_REMOVED
EVENTS_REVISED
CONTENT_CHANGED
COUNT_CHANGED
FETCH_FAILED
```

An alert can contain details about the affected event and the change that occurred.

Example:

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

Alerts are persisted in PostgreSQL and exposed through the dashboard. When notification delivery is enabled, the alert can also enter the notification outbox.

---

# 💬 Discord Notifications

The project deliberately separates **alert generation** from **notification delivery**.

```mermaid
flowchart LR
    A[USGS Data] --> B[Watcher]
    B --> C[Fingerprint]
    C --> D[Change Detection]
    D -->|Change| E[Alert Generator]
    E --> F[(PostgreSQL)]
    E --> G[Notification Outbox]
    G --> H[Notification Service]
    H --> I[Discord Webhook]
    I --> J[Discord Channel]
```

This architecture means the watcher can persist an alert without being responsible for delivering every notification.

### 💬 Join the Project Discord

[Join the Open Data Change Detector Discord Community](https://discord.gg/BGZ4KUmav)

---

# 📊 Streamlit Dashboard

The dashboard provides a visual monitoring interface backed by PostgreSQL.

It displays:

- 📌 Current dataset information
- 📈 Event-count history
- 🌎 Global earthquake map
- 🚨 Recent alerts
- ✏️ Revised events
- ⏱️ Fetch performance
- 📅 Snapshot history
- 🔎 Watch selection
- 🔄 Automatic refresh

The dashboard dynamically loads registered watches and displays watch-specific monitoring data.

## 🌎 Earthquake Visualization

The dashboard extracts geographic information from USGS GeoJSON records:

```text
Longitude
Latitude
Depth
Magnitude
Location
```

These values are used to display monitored earthquake events geographically.

---

# 📈 Historical Monitoring

Every monitoring run creates a snapshot.

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

Because snapshots and event-level state are retained, the system can show how the monitored dataset evolves instead of only showing its current state.

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
| **Git / GitHub** | Version control and source hosting |
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
├── requirements.txt
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
│   ├── send_notifications.py
│   ├── check_api_connection.py
│   ├── test_discord.py
│   ├── test_fetcher.py
│   ├── test_watches.py
│   │
│   └── watcher/
│       ├── __init__.py
│       ├── fetcher.py
│       ├── fingerprint.py
│       ├── watches.py
│       ├── db.py
│       ├── detectors.py
│       ├── notifier.py
│       └── discord_notifier.py
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

PostgreSQL runs locally through Docker Compose.

### Start

```bash
docker compose up -d
```

### Check

```bash
docker ps
```

### Stop

```bash
docker compose down
```

The database schema is defined in:

```text
sql/schema.sql
```

---

# ▶️ Running the Project

The following setup is the complete local workflow.

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd open-data-change-detector
```

## 2. Create and Activate a Virtual Environment

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create `.env` in the project root:

```env
DATABASE_URL=postgresql://watcher:password@localhost:5432/dataset_watcher
DISCORD_WEBHOOK_URL=your_webhook_url
```

### Security

Never commit the real `.env` file.

Keep database passwords, Discord webhook URLs, API credentials, access tokens, private keys, and other secrets out of source control.

Use `.env.example` with placeholder values instead.

## 5. Start PostgreSQL

```bash
docker compose up -d
```

Verify:

```bash
docker ps
```

## 6. Start the Watcher

```bash
python src/run_watcher.py
```

The watcher:

1. Loads configured watches.
2. Fetches the appropriate USGS dataset/feed.
3. Validates the response.
4. Generates a dataset fingerprint.
5. Loads the previous snapshot.
6. Compares event IDs and hashes.
7. Classifies added, removed, revised, and unchanged events.
8. Evaluates configured alert thresholds.
9. Saves snapshot and event-level state.
10. Creates alerts when required.
11. Adds notification records to the outbox.

## 7. Start the Notification Service

Open a second terminal:

```bash
python src/send_notifications.py
```

The service continuously checks the PostgreSQL notification outbox and sends pending alerts through the configured Discord webhook.

## 8. Start the Dashboard

Open a third terminal:

```bash
streamlit run src/dashboard.py
```

The dashboard reads monitoring state from PostgreSQL and presents charts, maps, events, alerts, and snapshot history.

---

# 🖥️ Recommended Terminal Setup

Run the three processes simultaneously:

### Terminal 1 — Watcher

```bash
python src/run_watcher.py
```

### Terminal 2 — Notification Service

```bash
python src/send_notifications.py
```

### Terminal 3 — Streamlit Dashboard

```bash
streamlit run src/dashboard.py
```

The resulting local workflow is:

```text
                         USGS
                           │
                           ▼
                    run_watcher.py
                           │
                           ▼
                 Fetch + Validate
                           │
                           ▼
                      Fingerprint
                           │
                           ▼
                   Change Detection
                           │
                           ▼
                      PostgreSQL
                      │          │
                      │          ▼
                      │    Notification Outbox
                      │          │
                      │          ▼
                      │   send_notifications.py
                      │          │
                      │          ▼
                      │       Discord
                      │
                      ▼
                Streamlit Dashboard
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
          Charts     Map     Alerts
```

---

# 🧪 Testing

The project uses **pytest** for automated testing.

Run:

```bash
pytest
```

The tests cover important areas including:

- Watch configuration
- Query generation
- Data fetching
- Fingerprinting
- Change detection
- Dataset comparison

A successful test run should complete without failures.

---

# 🔐 Environment Variables

Required configuration:

```env
DATABASE_URL=postgresql://watcher:password@localhost:5432/dataset_watcher
DISCORD_WEBHOOK_URL=your_webhook_url
```

Recommended repository setup:

```text
.env
.env.example
.gitignore
```

Example `.gitignore` entries:

```gitignore
.env
.venv/
__pycache__/
*.pyc
```

Never commit real credentials or webhook URLs.

---

# 🛑 Stopping the Project

Stop the three Python processes from their respective terminals.

Then stop PostgreSQL:

```bash
docker compose down
```

To start it again:

```bash
docker compose up -d
```

---

# ⚡ Quick Start

After the repository has already been configured:

```powershell
.venv\Scripts\activate
```

```bash
docker compose up -d
```

In Terminal 1:

```bash
python src/run_watcher.py
```

In Terminal 2:

```bash
python src/send_notifications.py
```

In Terminal 3:

```bash
streamlit run src/dashboard.py
```

Run tests whenever required:

```bash
pytest
```

---

# 🌐 Data Source

The project currently uses the **USGS Earthquake Hazards Program**.

### Historical Earthquake API

Used by the rolling seven-day watch:

```text
USGS FDSN Event API
```

### Real-Time Earthquake Feed

Used by the live watch:

```text
USGS all_hour.geojson
```

The architecture is intentionally separated from the data source so additional open-data connectors can be integrated later.

---

# 🧠 Data Engineering Concepts Demonstrated

| Concept | Implementation |
|---|---|
| API ingestion | Fetch structured data from external APIs and feeds |
| Data validation | Validate incoming responses before processing |
| Data fingerprinting | Represent dataset state with hashes and metadata |
| Change detection | Compare current state with historical state |
| Event-level state tracking | Track individual records across snapshots |
| Database persistence | Store monitoring state in PostgreSQL |
| Alerting | Generate structured alerts for unexpected changes |
| Observability | Track fetch status, duration, counts, history, and alerts |
| Visualization | Monitor system state through Streamlit |
| Containerization | Run PostgreSQL through Docker |
| Configuration management | Define watches and thresholds in YAML |
| Notification architecture | Decouple alert generation from delivery |

---

# 🔬 Example Detection Scenario

Suppose:

```text
Previous Snapshot
Events: 304
```

The next run returns:

```text
Current Snapshot
Events: 305
```

The detector identifies:

```text
+1 new event
```

The system can store the new event's:

```text
Event ID
Event fingerprint
Event data
Snapshot ID
Alert information
```

If the configured threshold requires a notification, the alert is placed into the notification outbox and can be delivered to Discord.

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

The event ID is unchanged, but its fingerprint changes.

The detector identifies:

```text
EVENTS_REVISED
```

and records:

```text
Field: magnitude
Before: 4.8
After:  5.0
```

This is a key difference between this project and a simple row-count monitoring script.

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

[▶️ Watch the Full Dashboard Demo](docs/demo/dashboard-demo.mp4)

---

# 🔮 Future Improvements

Potential extensions include:

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

A production deployment could evolve toward:

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

This could eventually support multiple datasets, scheduled workers, centralized monitoring, cloud storage, and production-grade observability.

---

# 📈 Why This Project Matters

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

Possible areas include:

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
