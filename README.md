# okDRIVER — Autonomous Road Distress & Pothole Reporting Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20Neon-336791.svg?logo=postgresql&logoColor=white)](https://neon.tech)
[![YOLOv8](https://img.shields.io/badge/Computer%20Vision-YOLOv8%20(Ultralytics)-FF6F00.svg)](https://ultralytics.com)
[![Cloudflare R2](https://img.shields.io/badge/Object%20Storage-Cloudflare%20R2%20%2F%20S3-F38020.svg?logo=cloudflare&logoColor=white)](https://cloudflare.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**okDRIVER** is an end-to-end, full-stack civic infrastructure intelligence platform that detects road hazards and potholes from road photos or vehicle dashcam video feeds, tags them with granular GPS coordinates and administrative boundaries, automatically identifies the responsible civic authority (NHAI, State PWD, Nagar Palika, MCD, BMC), and dispatches automated incident alerts via Telegram, Email, and REST APIs.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Our Approach & Methodology](#our-approach--methodology)
- [Performance & Cloud Optimizations](#performance--cloud-optimizations)
- [Repository Structure](#repository-structure)
- [Quick Start Guide](#quick-start-guide)
  - [1-Click Windows Launch](#1-click-windows-launch-recommended)
  - [Manual Local Setup](#manual-local-setup)
  - [Docker Compose](#docker-compose)
- [Environment Configuration](#environment-configuration)
- [API Reference](#api-reference)
- [Deployment Guide](#deployment-guide)

---

## System Architecture

```
                       Vehicle Dashcam / Mobile Camera Feed
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │       Client-Side Pre-Compression         │
                  │       (HTML5 Canvas in Browser)           │
                  │   Scales >1280px photos to save bandwidth │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │    okDRIVER Vision Pipeline (YOLOv8)      │
                  │    • In-Memory Singleton & Warmup         │
                  │    • Non-blocking asyncio.to_thread       │
                  │    • Severity Rating (LOW to CRITICAL)    │
                  └─────────────────────┬─────────────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
           ┌───────────────────────────┐ ┌───────────────────────────┐
           │ Cloud Media Storage       │ │ Reverse Geocoding Engine  │
           │ (Cloudflare R2 / AWS S3)  │ │ (OSM Nominatim + LRU)     │
           │ Stores raw & annotated    │ │ Distinguishes NHAI, State │
           │ video frames & photos     │ │ PWD, Nagar Palika, MCD... │
           └─────────────┬─────────────┘ └─────────────┬─────────────┘
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │            FastAPI REST Engine            │
                  │    • Ingestion, CRUD, Audit Trail Logs    │
                  │    • Multi-Channel Alerting Router        │
                  │    • Explicit Memory Garbage Collection   │
                  └──────────────┬──────────────────┬─────────┘
                                 │                  │
                ┌────────────────┴──────┐           └──────────────────┐
                ▼                       ▼                              ▼
  ┌───────────────────────────┐ ┌──────────────────────────┐ ┌───────────────────────────┐
  │ Neon Cloud PostgreSQL     │ │ Automated Civic Alerts   │ │ Next.js 16 Web Dashboard  │
  │ • Potholes & Telemetry    │ │ • Telegram Group Push    │ │ • Interactive Leaflet Map │
  │ • Status Change Audit Log │ │ • Gmail SMTP Dispatch    │ │ • Incident Dossier Views  │
  │ • Municipal Ticket Records│ │ • Simulated Authority API│ │ • Zone & Severity Filters │
  └───────────────────────────┘ └──────────────────────────┘ └───────────────────────────┘
```

---

## Our Approach & Methodology

okDRIVER implements a modular, four-stage civic infrastructure monitoring pipeline:

### 1. Computer Vision & Automated Defect Ingestion
- **Model Architecture:** Uses a fine-tuned **YOLOv8** object detection model capable of locating road defects from single photos (`JPG`, `PNG`, `WEBP`) or dashcam video streams (`MP4`, `MOV`, `AVI`).
- **Telemetry Extraction:** Automatically extracts latitude, longitude, and timestamp from image EXIF metadata, or binds live device GPS and vehicle speed (`km/h`).
- **Visual Evidence Overlays:** Generates annotated evidence images with high-visibility bounding boxes, confidence badges, and geographic watermarks.

### 2. Physical Severity & Hazard Calculation
Rather than treating all potholes equally, okDRIVER calculates physical hazard metrics:
- **Relative Footprint:** Bounding box pixel dimensions are calculated relative to the total camera frame area.
- **Continuous Score (`0.0` to `10.0`):** Combines detection confidence, surface footprint, and vehicle speed into a hazard score.
- **Categorical Tiers:**
  - `CRITICAL` (Score $\ge 8.0$): Immediate severe accident risk, deep craters, high-speed road defects.
  - `HIGH` (Score $6.0 - 7.9$): Substantial surface hazard requiring prompt repair.
  - `MEDIUM` (Score $3.0 - 5.9$): Developing road erosion.
  - `LOW` (Score $< 3.0$): Surface crack or minor defect.

### 3. Dynamic Reverse Geocoding & Municipal Routing
A major challenge in road maintenance is identifying **who owns the road**. okDRIVER dynamically resolves the responsible authority:
- **National Highways (`NH`):** Automatically routed to the **National Highways Authority of India (NHAI)**.
- **State Highways (`SH`):** Routed to the respective **State Public Works Department (State Highway Division)**.
- **Metros:** Bounding-box matching routes to major corporations: **MCD** (Delhi), **BMC** (Mumbai), **BBMP** (Bengaluru).
- **Tier-2 & Tier-3 Towns:** Resolves to the local **Nagar Palika Parishad** or **Nagar Nigam** (e.g., Alwar, Hathras).
- **Rural/District Roads:** Assigned to the local **District PWD Division**.
- **In-Memory Caching:** Uses an LRU cache (`@lru_cache(maxsize=1024)`) rounded to 4 decimal places (~11 meters) to eliminate redundant external geocoding requests during video processing.

### 4. Automated Multi-Channel Alerting & Lifecycle Tracking
- **Telegram Push Notifications:** Dispatches structured incident reports directly to municipal control rooms with Google Maps links, defect photo attachments, and direct buttons to web incident dossiers.
- **Email Notifications (SMTP):** Sends formatted maintenance dispatch notices with HTML email templates and plain-text fallback.
- **Audit Trail:** Every status change (`DETECTED` $\rightarrow$ `REPORTED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `RESOLVED`) is logged in the database with timestamps, notes, and actor attribution.

---

## Performance & Cloud Optimizations

okDRIVER is engineered to operate smoothly on resource-constrained cloud hosting (such as **Render's Free Tier** with 512MB RAM and shared CPU) without sacrificing detection accuracy:

| Technique | Where It Runs | Purpose & Real-World Impact |
| :--- | :--- | :--- |
| **Model Singleton** | `backend/app/main.py` | Loads YOLO once during startup into RAM instead of reading 22MB weights from disk on every upload. Saves 1.5s per request. |
| **Boot Warmup** | `backend/app/main.py` | Runs a dummy zero-array inference at server startup, eliminating the 3–5 second cold-start lag for the first user. |
| **Non-Blocking Threadpool** | `backend/app/api/.../potholes.py` | Runs `detector.detect()` inside `asyncio.to_thread()`, preventing YOLO from freezing the event loop so health checks never time out. |
| **Client-Side Pre-Compression** | `frontend/components/IngestModal.js` | HTML5 `<canvas>` compresses smartphone photos (>1280px) in the browser before upload. Drops payload from ~10MB to ~200KB (95% bandwidth savings). |
| **Adaptive Video Sampling** | `backend/app/api/.../potholes.py` | Samples 10 keyframes on CPU (vs. 25 on GPU), completing video analysis in ~7 seconds and preventing cloud gateway timeouts. |
| **Memory Garbage Collection** | `backend/app/api/.../potholes.py` | Calls `gc.collect()` after processing images to instantly free OpenCV memory buffers, keeping RAM well under 512MB. |

---

## Repository Structure

```
okDRIVER/
├── okdriver/                     # Core Python Detection Package
│   ├── detector.py               # PotholeDetector (YOLOv8 wrapper, adaptive device selector)
│   ├── severity.py               # SeverityCalculator (hazard scoring logic)
│   ├── visualizer.py             # annotate_frame (bounding boxes, telemetry watermarks)
│   └── utils.py                  # EXIF GPS parser & model download manager
│
├── backend/                      # FastAPI REST API Backend
│   ├── app/
│   │   ├── api/v1/endpoints/     # REST routes (potholes, health, analytics)
│   │   ├── crud/                 # Database queries and audit log creation
│   │   ├── models/               # SQLAlchemy models (PotholeRecord, PotholeReport)
│   │   ├── schemas/              # Pydantic v2 validation schemas
│   │   ├── services/             # Storage (Cloudflare R2), Authorities (OSM), Alerts (Telegram/Email)
│   │   ├── config.py             # App settings & environment loader
│   │   ├── database.py           # Engine & SessionLocal (Neon PostgreSQL + SQLite fallback)
│   │   └── main.py               # FastAPI app, lifespan singleton & warmup
│   ├── requirements.txt          # Python dependencies
│   ├── run_server.py             # Standalone server launcher
│   └── seed_data.py              # Test incident seeder
│
├── frontend/                     # Next.js 16 Web Dashboard
│   ├── app/                      # App router (homepage, analytics, incident dossier)
│   ├── components/               # UI components (MapView, DataTable, IngestModal, IncidentCard)
│   ├── lib/api.js                # API client connector
│   └── package.json              # Frontend dependencies
│
├── run.bat                       # 1-Click Windows execution script
├── Dockerfile                    # Containerization definition
├── docker-compose.yml            # Multi-service composition
└── README.md                     # Documentation
```

---

## Quick Start Guide

### 1-Click Windows Launch (Recommended)

If you are on Windows, simply double-click **`run.bat`** or run:

```powershell
./run.bat
```

This starts:
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)

---

### Manual Local Setup

#### Prerequisites
- **Python 3.10 to 3.14**
- **Node.js 18+** and **npm**

#### Step 1: Backend Setup
```bash
# 1. Navigate to backend
cd backend

# 2. Install dependencies
pip install -r requirements.txt
pip install -e ..

# 3. Create .env file (copy from .env.example)
cp .env.example .env

# 4. (Optional) Seed demo incidents
python seed_data.py

# 5. Start FastAPI server
python run_server.py
```
- API Root: [http://localhost:8000](http://localhost:8000)
- Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc Documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### Step 2: Frontend Setup
```bash
# Open a new terminal
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
- Dashboard: [http://localhost:3000](http://localhost:3000)

---

### Docker Compose

Run the entire platform in isolated containers:

```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

---

## Environment Configuration

Configure variables in `backend/.env`:

```env
# Database (Neon Cloud PostgreSQL or local fallback)
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>/<database>?sslmode=require
ENABLE_SQLITE_FALLBACK=true

# Object Storage (Cloudflare R2 / AWS S3)
R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<your_key_id>
R2_SECRET_ACCESS_KEY=<your_secret_key>
R2_BUCKET_NAME=potholeimage

# SMTP Email Alerting
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com

# Telegram Push Alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_DEFAULT_CHAT_ID=your_chat_or_group_id

# Server Settings
HOST=0.0.0.0
PORT=8000
FRONTEND_URL=http://localhost:3000
```

---

## API Reference

### Detection & Ingestion
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/potholes/detect-and-store` | Upload image/video for live YOLO inference, cloud evidence storage, and DB persistence. |
| `POST` | `/api/v1/potholes/ingest` | Ingest structured detection telemetry JSON from an external client. |

### Incident Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/potholes/` | Filtered & paginated list of defects (by severity, status, authority, bounding box). |
| `GET` | `/api/v1/potholes/{id}` | Full incident dossier with telemetry, bounding box, and history audit log. |
| `PATCH`| `/api/v1/potholes/{id}/status` | Transition status (`REPORTED`, `ACKNOWLEDGED`, `IN_PROGRESS`, `RESOLVED`). |
| `DELETE`| `/api/v1/potholes/{id}` | Remove defect record. |

### Analytics & Reporting
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/potholes/stats/summary` | Aggregate defect counts grouped by severity, status, and average confidence. |
| `POST` | `/api/v1/potholes/{id}/report` | Manually dispatch Telegram/Email alert for a defect. |
| `POST` | `/api/v1/potholes/auto-report-critical`| Batch dispatch alerts for all un-reported critical hazards. |
| `GET` | `/api/v1/health` | Service health status and database connectivity check. |

---

## Deployment Guide

### Deploy Backend to Render (Free Tier)
1. Link your GitHub repo to [Render](https://render.com).
2. Choose **Web Service** $\rightarrow$ **Python**.
3. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt && pip install -e ..`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from your `.env` file.
5. Render will automatically build and host the API within the 512MB RAM free tier limit.

### Deploy Frontend to Vercel
1. Link your repo to [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://your-backend.onrender.com`
4. Click **Deploy**.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
