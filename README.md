# Smart Theft Detection System

A computer vision-based theft detection system that analyzes CCTV footage and **live camera feeds** to identify suspicious behaviors and generate real-time alerts.

## ✨ Key Features

- 📹 **Real-time Live Detection** - Monitor camera feeds with instant object detection
- 📁 **Video Upload & Analysis** - Process pre-recorded footage for detailed analysis
- 🎯 **Person & Product Detection** - YOLOv8-based object detection
- 🤸 **Pose Estimation** - MediaPipe body tracking for gesture analysis
- 🔍 **Interaction Detection** - Recognizes shelf/pocket/bag interactions
- ⚠️ **Suspicion Scoring** - AI-powered behavioral analysis
- 📊 **Dashboard & Analytics** - Real-time statistics and alerts
- 🎬 **Evidence Management** - Automatic clip extraction and snapshots

## 🏗️ Architecture

The system implements an 8-layer architecture, processing video through multiple stages to detect and alert on suspicious behaviors:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: Video Input Layer                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  • Captures video from CCTV/uploaded files                   │  │
│  │  • Extracts frames at configurable FPS (default 10 FPS)      │  │
│  │  • Preprocesses frames for detection (resize to 640x640)     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2: Person Detection Layer (YOLOv8)                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  • Detects persons in each frame                             │  │
│  │  • Extracts bounding boxes with confidence scores            │  │
│  │  • Filters detections > 0.5 confidence threshold             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3: Pose Estimation Layer (MediaPipe)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  • Extracts 33 body landmarks for each detected person       │  │
│  │  • Focuses on hands, elbows, shoulders, hips                 │  │
│  │  • Normalizes coordinates relative to person bbox            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4: Human-Object Interaction                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  • Detects hand positions in zones (shelf/pocket/bag)        │  │
│  │  • Classifies actions (reaching/grabbing/concealing)         │  │
│  │  • Tracks movement patterns and dwell time                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 5: Suspicious Behavior Detection Engine                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Behavior Matrix Scoring:                                     │  │
│  │  • Base: Hand near shelf (+30 points)                        │  │
│  │  • Critical: Shelf → Pocket (+40 points)                     │  │
│  │  • Critical: Shelf → Bag (+20 points)                        │  │
│  │  • Repeated shelf touches (+10 points)                       │  │
│  │  • Concealing motions (+10 points)                           │  │
│  │  → Alert triggered if Score > 70                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 6: Alert Generation System                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  • Creates alert with suspicion score and reason             │  │
│  │  • Generates snapshot with bounding boxes                    │  │
│  │  • Creates 10-second video clip (5s before + 5s after)       │  │
│  │  • Stores evidence in database                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 7: Backend API Layer (FastAPI)                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  REST Endpoints:                                              │  │
│  │  • GET  /api/alerts/     - List alerts with filters          │  │
│  │  • GET  /api/alerts/{id} - Get alert details                 │  │
│  │  • PATCH /api/alerts/{id} - Update alert status              │  │
│  │  • POST /api/videos/upload - Upload video                    │  │
│  │  • GET  /api/stats/      - Dashboard statistics              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 8: Web Dashboard (React + TypeScript)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  • Video Upload Interface with progress tracking             │  │
│  │  • Alert Cards Grid with snapshots and scores                │  │
│  │  • Event Timeline visualization                              │  │
│  │  • Statistics Panel (total alerts, avg score, trends)        │  │
│  │  • Alert Modal with video playback and event logs            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🎯 Detection Logic

**Suspicious Behavior Patterns:**
- ✅ Hand moves from shelf → pocket (High Risk: Score +70)
- ✅ Hand moves from shelf → bag (Medium Risk: Score +50)
- ✅ Repeated shelf touching (Score +10)
- ✅ Concealing hand motions (Score +10)
- ❌ Normal browsing (No alert)

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL 14+ (or SQLite for development)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

### Download ML Models

```bash
# YOLOv8n model will be auto-downloaded on first run
# Or manually:
cd ml_models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

## Project Structure

```
SMART-THEFT_DETECTION/
├── backend/          # FastAPI backend
├── frontend/         # React dashboard
├── ml_models/        # Pre-trained models
├── data/            # Video storage and evidence
└── tests/           # Test suite
```

## Features

- Real-time suspicious behavior detection
- Alert generation with video evidence
- Interactive timeline visualization
- Dashboard analytics and statistics
- Snapshot and video clip creation

## Backend Startup (Windows)

Always start backend from the project root using:

```bat
start-backend.bat
```

This ensures the server runs with the correct working directory (`backend`) so hot-reload can import `app.main` reliably.

## License

MIT
