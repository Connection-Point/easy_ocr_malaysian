# SmartPark LPR — Malaysian License Plate Recognition Parking System

A fully automated, AI-powered smart parking management system for Malaysian vehicles. It uses a live webcam feed with dual-mode OCR to recognize license plates, manage vehicle check-in/check-out, calculate fees, and display everything on a real-time web dashboard.

---

## Features

- **Dual-Mode OCR Engine**
  - **Fast Mode** — EasyOCR for real-time, low-latency plate detection
  - **Precise Mode** — Qwen2-VL (local LLM) for high-accuracy recognition in difficult conditions
- **Malaysian Plate Correction** — Smart character substitution (e.g. `0->D`, `8->B`) based on Malaysian plate standards
- **Automated Fee Calculation** — Tiered pricing with configurable first-hour rate, additional-hour rate, and grace period
- **Real-Time Web Dashboard** — FastAPI + Chart.js dashboard with:
  - Revenue tracker chart (Hourly / Daily / Weekly / Monthly filters)
  - Car entries over time chart
  - Recent activity log
  - Full CRUD for parking records, pricing schemes, and system parameters
- **MySQL Backend** — Auto-initializes the database and all tables on first run
- **Clean Shutdown** — Pressing `Q` kills both the camera feed and the dashboard server together

---

## Project Structure

```
PlateRecog/
├── LPR.py                  # Main entry point — camera feed, key controls, launches dashboard
├── lpr_dashboard_web.py    # FastAPI web server & REST API
├── db_manager.py           # MySQL connection config & database initialization
├── parking_logic.py        # Fee calculation & check-in/check-out business logic
├── download_model.py       # Helper script to download the Qwen2-VL model
├── requirements.txt        # Python dependencies
└── static/
    ├── index.html          # Dashboard frontend
    ├── app.js              # Dashboard JS logic (Charts, API calls, modals)
    └── styles.css          # Dashboard styling
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.9 or later |
| MySQL Server | 8.0+ running locally |
| Webcam | Any USB or built-in camera |
| RAM | 8 GB minimum (16 GB recommended for Precise mode) |
| GPU | Optional — CPU inference is supported for Precise mode |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/PlateRecog.git
cd PlateRecog
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the database

Open `db_manager.py` and update the credentials to match your MySQL setup:

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD',   # <-- update this
    'database': 'lpr_testing'
}
```

> The database and all tables are **created automatically** on first run. No manual SQL setup is needed.

### 5. Download the Qwen2-VL model *(required for Precise mode only)*

```bash
python download_model.py
```

> This downloads the model weights into a `model/` folder. It may take a while depending on your connection speed.  
> **Fast mode (EasyOCR) works without this step.**

---

## Running the System

```bash
python LPR.py
```

This will:
1. Initialize the database (creates tables if they don't exist)
2. Start the web dashboard at `http://localhost:8005` (auto-opens in browser)
3. Open the live webcam feed window

---

## Camera Window Controls

| Key | Action |
|-----|--------|
| `S` | Scan the current frame for a license plate |
| `G` | Toggle the gate between **IN** (entry) and **OUT** (exit) |
| `M` | Toggle OCR engine between **Fast** (EasyOCR) and **Precise** (Qwen2-VL) |
| `Q` | Quit — closes the camera feed and shuts down the dashboard server |

---

## Web Dashboard

Access the dashboard at: **http://localhost:8005**

| Section | Description |
|---|---|
| **Dashboard** | Revenue chart, entries chart, and recent activity table |
| **Parking Scheme** | Manage pricing tiers (first hour rate, additional hour rate, grace period) |
| **System Params** | View and edit system status codes (Active, Deactivated, Paid, Unpaid) |
| **All Records** | Full table of all parking records with edit and delete actions |

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard` | Dashboard stats, entry counts, and recent records |
| `GET` | `/api/revenue?filter=hourly` | Revenue data — filters: `hourly`, `daily`, `weekly`, `monthly` |
| `GET/POST/PUT/DELETE` | `/api/records/{id}` | Parking records CRUD |
| `GET/POST/PUT/DELETE` | `/api/scheme/{id}` | Parking scheme CRUD |
| `GET/POST/PUT/DELETE` | `/api/sysparam/{code}` | System parameter CRUD |

---

## Fee Calculation Logic

| Scenario | Fee |
|---|---|
| Duration <= Grace Period (default: 15 min) | Free |
| Duration <= 1 hour | First Hour Rate (default: RM 3.00) |
| Duration > 1 hour | First Hour Rate + (extra hours x Additional Hour Rate) |

All rates and the grace period are configurable from the **Parking Scheme** section of the dashboard.

---

## Troubleshooting

**Camera not detected**
- Make sure no other app is using the webcam
- The system tries `CAP_DSHOW` first, then falls back to the default OpenCV backend

**Dashboard does not open**
- Check that port `8005` is not already in use
- Open `http://localhost:8005` manually in your browser

**Precise mode fails to load**
- Make sure you have run `download_model.py` and the `model/` folder exists
- The system will attempt a CPU fallback automatically if no GPU is found

**MySQL connection error**
- Verify MySQL is running (`net start mysql` on Windows)
- Double-check credentials in `db_manager.py`

---

## Tech Stack

| Layer | Technology |
|---|---|
| OCR (Fast) | [EasyOCR](https://github.com/JaidedAI/EasyOCR) |
| OCR (Precise) | [Qwen2-VL](https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct) via Transformers |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| Database | MySQL + mysql-connector-python |
| Frontend | HTML5, Vanilla JS, CSS3, [Chart.js](https://www.chartjs.org/) |
| Computer Vision | [OpenCV](https://opencv.org/) |

---

## License

This project is open source. Feel free to fork and adapt it for your own use.
