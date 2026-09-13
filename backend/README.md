# okDRIVER - Backend API

Production-grade FastAPI & PostgreSQL backend for okDRIVER pothole detection, telemetry storage, and lifecycle management.

---

## Features

- **Civic Authority Assignment**: Automatically assigns detected potholes to responsible municipal authorities based on geographic location (e.g. BMC Mumbai, MCD Delhi, BBMP Bengaluru, SFDPW San Francisco, PWD Central fallback).
- **Automated Incident Reporting System**:
  - Generates comprehensive municipal hazard reports with GPS, timestamp, severity, confidence, photo evidence URLs, and structured email bodies (text + rich HTML).
  - Dispatches reports via simulated authority API (returning external municipal reference IDs and SLA targets) or email channel.
  - Automatically tracks generated ticket IDs (`TKT-{CODE}-{DATE}-{ID}`) and reporting lifecycle statuses (`UNREPORTED`, `REPORTED`, `ACKNOWLEDGED`).
- **Phase 1 Ingestion**: Ingests JSON detection outputs from `okdriver.PotholeDetector` (`PotholeDetectionResult`), extracting telemetry, bounding box geometry, severity ratings, and evidence image references.
- **Evidence Storage**: Automated handling of captured image evidence and visually annotated overlays with static file serving (`/static/evidence/...`).
- **Live Detect & Store**: Direct endpoint (`POST /api/v1/potholes/detect-and-store`) to process uploaded images with YOLO, annotate detections, and record them in the database in a single call.
- **Full CRUD API**:
  - `POST /api/v1/potholes/`: Manual pothole creation.
  - `GET /api/v1/potholes/`: Paginated listing with multi-attribute filtering (`status`, `severity`, `min_confidence`, `authority_code`, `report_status`, date range, geographic bounding box).
  - `GET /api/v1/potholes/{id}`: Single record detail.
  - `PATCH /api/v1/potholes/{id}`: Operational status transitions (`DETECTED` -> `VERIFIED` -> `IN_PROGRESS` -> `REPAIRED` -> `REJECTED`) and repair notes.
  - `DELETE /api/v1/potholes/{id}`: Record deletion.
  - `GET /api/v1/potholes/stats/summary`: Aggregate analytics across the dataset.
- **Database Support**: Built for PostgreSQL with automatic fallback to local SQLite for development and testing.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure Database

By default, the backend connects to PostgreSQL at:
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/okdriver
```
*(If PostgreSQL is not running, the server automatically falls back to local SQLite at `backend/okdriver_dev.db`.)*

To start a PostgreSQL instance with Docker:
```bash
docker run --name okdriver-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=okdriver -p 5432:5432 -d postgres:16
```

### 3. Launch Server

```bash
python backend/run_server.py
```
Or directly using Uvicorn:
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

### 4. Interactive API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## Running Backend Tests

Run all unit and integration tests with `pytest`:

```bash
python -m pytest backend/tests/test_reporting.py backend/tests/test_api.py -v
```

---

## API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System and database health status |
| `POST` | `/api/v1/potholes/ingest` | Ingest Phase 1 detection JSON (auto-assigns authority) |
| `POST` | `/api/v1/potholes/ingest/upload` | Multipart upload (image evidence + Phase 1 JSON) |
| `POST` | `/api/v1/potholes/detect-and-store` | Upload image, run YOLO detection, and store findings |
| `POST` | `/api/v1/potholes/` | Create a pothole record manually (auto-assigns authority) |
| `GET` | `/api/v1/potholes/` | List potholes with filtering (including `authority_code`, `report_status`) |
| `GET` | `/api/v1/potholes/{id}` | Get pothole record by ID |
| `PATCH` | `/api/v1/potholes/{id}` | Update status, severity, or repair notes |
| `DELETE` | `/api/v1/potholes/{id}` | Delete a pothole record |
| `POST` | `/api/v1/potholes/{id}/report` | Generate and dispatch incident report to civic authority |
| `POST` | `/api/v1/potholes/auto-report-critical` | Auto-dispatch reports for all un-reported critical/high hazards |
| `GET` | `/api/v1/reports` | List dispatched reports and tickets |
| `GET` | `/api/v1/reports/{ticket_id}` | Retrieve report data, evidence links, and dispatch logs |
| `GET` | `/api/v1/authorities` | List configured civic authorities and jurisdiction boundaries |
| `GET` | `/api/v1/potholes/stats/summary` | Analytics & distribution summary |

