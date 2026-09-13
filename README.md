# okDRIVER — Autonomous Road Distress & Pothole Reporting Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20Neon-336791.svg?logo=postgresql&logoColor=white)](https://neon.tech)
[![YOLOv8](https://img.shields.io/badge/Computer%20Vision-YOLOv8%20(Hugging%20Face)-FF6F00.svg)](https://huggingface.co)
[![Cloudflare R2](https://img.shields.io/badge/Object%20Storage-Cloudflare%20R2%20%2F%20AWS%20S3-F38020.svg?logo=cloudflare&logoColor=white)](https://cloudflare.com)
[![Docker](https://img.shields.io/badge/Container-Docker%20%26%20Compose-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)

**okDRIVER** is an end-to-end, full-stack civic infrastructure platform that automatically detects road hazards and potholes from mobile or dashcam video feeds, tags them with granular GPS and reverse-geocoded municipal jurisdictions (MCD, BMC, BBMP, Nagar Palika, NHAI, State PWD), and dispatches automated incident alerts to responsible civic departments via Telegram, Email, and REST APIs.

---

## System Architecture

```
                       Vehicle Dashcam / Mobile Camera Feed
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │    okDRIVER Vision Pipeline (YOLOv8)      │
                  │    • Bounding Box & Area Footprint Metric  │
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
                  │    FastAPI REST Engine (Hugging Face)     │
                  │    • Ingestion, CRUD, Audit Trail Logs    │
                  │    • Multi-Channel Dispatch Router        │
                  └──────────────┬──────────────────┬─────────┘
                                 │                  │
                ┌────────────────┴──────┐           └──────────────────┐
                ▼                       ▼                              ▼
  ┌───────────────────────────┐ ┌──────────────────────────┐ ┌───────────────────────────┐
  │ Neon Cloud PostgreSQL     │ │ Automated Civic Alerts   │ │ Next.js 16 Web Dashboard  │
  │ • Potholes & Telemetry    │ │ • Telegram Push (Group)  │ │ • Interactive Leaflet Map │
  │ • Status Change Audit Log │ │ • Gmail SMTP Dispatch    │ │ • Incident Dossier Views  │
  │ • Municipal Ticket Records│ │ • Simulated Authority API│ │ • Zone & Severity Filters │
  └───────────────────────────┘ └──────────────────────────┘ └───────────────────────────┘
```

---

## Key Features

1. **Computer Vision & Open-Source AI Model:**
   - Pre-trained **YOLOv8** pothole detection model weights sourced from **Hugging Face**.
   - Dual-input support: Single road photos (`JPG`, `PNG`) and continuous dashcam video streams (`MP4`, `MOV`, `AVI`).
   - Generates visual overlays with bounding boxes, confidence badges, and telemetry watermarks.

2. **Automated Severity Scoring:**
   - Computes continuous numerical severity scores (`0.0` to `10.0`) and categorical ratings (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) based on bounding-box footprint relative to camera frame dimensions.

3. **Dynamic Reverse Geocoding & Municipal Routing:**
   - Dynamic boundary resolution mapping GPS points to responsible civic authorities:
     - **National Highways (`NH`):** Routed to **National Highways Authority of India (NHAI)**.
     - **State Highways (`SH`):** Routed to **State PWD (State Highway Division)**.
     - **Metros:** **MCD** (Delhi NCR), **BMC** (Mumbai), **BBMP** (Bengaluru).
     - **Tier-2 & Tier-3 Towns:** Resolves to local **Nagar Palika Parishad** or **Nagar Nigam** (e.g. Alwar, Hathras).
   - In-memory LRU caching (`@lru_cache`) executes sub-millisecond route matching.

4. **Multi-Channel Incident Dispatch:**
   - **Telegram Push Alerts:** Real-time push notifications delivered directly to control room groups (with Google Maps directions and web incident dossier buttons).
   - **Gmail SMTP Dispatch:** Professional road maintenance dispatch emails with structured HTML and plain-text fallback.
   - **Simulated Municipal API:** Instant mock authority ticket generation (`TKT-MCD-YYYYMMDD-XXXXXX`).

5. **Operational Lifecycle Tracking Dashboard:**
   - Interactive **Leaflet Map** with color-coded severity markers (Red = Critical, Orange = High, Yellow = Medium, Green = Low).
   - Full audit trail tracking transitions (`DETECTED` $\rightarrow$ `REPORTED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `REPAIRED`) with actor attribution and inspection notes.

---

## Tech Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | Next.js 16, React 19, TailwindCSS, Leaflet, React-Leaflet |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0 |
| **Machine Learning** | YOLOv8 (Ultralytics / Hugging Face), OpenCV, PyTorch, Pillow |
| **Cloud Database** | PostgreSQL (Neon Cloud Serverless PostgreSQL) |
| **Object Storage** | Cloudflare R2 / AWS S3 (`boto3` S3-compatible API) |
| **Containerization** | Docker, Docker Compose (Hugging Face Spaces compatible) |
| **Alerting** | Telegram Bot API, Gmail SMTP, Municipal REST Ticket API |

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```env
# Database (Neon Cloud PostgreSQL)
DATABASE_URL=postgresql+psycopg2://neondb_owner:password@ep-solitary-grass-xxxx.neon.tech/neondb?sslmode=require

# Cloudflare R2 / AWS S3 Media Storage
R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<your_r2_access_key>
R2_SECRET_ACCESS_KEY=<your_r2_secret_key>
R2_BUCKET_NAME=potholeimage

# SMTP Email Alerting
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com

# Telegram Push Alerts
TELEGRAM_BOT_TOKEN=8837174299:AAGbvuRoW8h13Wt46Dhz_T_TN0x4MCbWNSc
TELEGRAM_DEFAULT_CHAT_ID=-5567080146

# Server Settings
HOST=0.0.0.0
PORT=8000
FRONTEND_URL=http://localhost:3000
```

---

## Running Locally

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
pip install -e ..

# Seed database with realistic incidents & geocoded authorities
python seed_data.py

# Start FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc API Documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 1-Command Deployment via Docker Compose

```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`

---

## Cloud Deployment Guide

### A. Deploy AI Backend to Hugging Face Spaces (16 GB RAM Free)
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) $\rightarrow$ **Create new Space**.
2. Select **Docker** as Space SDK.
3. Push the repository. The included [`Dockerfile`](file:///c:/Users/yashs/Desktop/okDRIVER/Dockerfile) will automatically build and expose port `7860`.
4. In Space **Settings $\rightarrow$ Variables and Secrets**, add:
   - `DATABASE_URL` (from Neon)
   - `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` (from Cloudflare R2)
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_DEFAULT_CHAT_ID`
5. Ping `https://your-space.hf.space/api/v1/health` with **UptimeRobot** (every 5 minutes) to ensure 24/7 uptime without sleep.

### B. Deploy Frontend to Vercel
1. Go to [vercel.com](https://vercel.com) $\rightarrow$ **Add New Project**.
2. Connect your GitHub repository and select the `frontend/` directory.
3. Set the Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://your-space.hf.space` (or your live backend URL).
4. Click **Deploy**.

---

## Automated Tests

Run backend unit and integration tests:
```bash
pytest backend/tests -v
```

---

## License & Attribution
- Open-source detection model adapted from Ultralytics YOLOv8.
- Reverse geocoding telemetry powered by OpenStreetMap Nominatim.
