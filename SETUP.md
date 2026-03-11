# Smart Theft Detection System - Setup Guide

## Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- Git

## Backend Setup

### 1. Navigate to backend directory
```bash
cd backend
```

### 2. Create virtual environment
```bash
python -m venv venv
```

### 3. Activate virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure environment
```bash
copy .env.example .env
```

Edit `.env` file as needed. For development, the defaults work fine.

### 6. Run the backend server
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

Visit `http://localhost:8000/docs` for interactive API documentation.

## Frontend Setup

### 1. Navigate to frontend directory
```bash
cd frontend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Start development server
```bash
npm start
```

The dashboard will open at `http://localhost:3000`

## Testing the System

### 1. Prepare test video
Place a video file (MP4, AVI, MOV) in the `data/sample_videos/` directory.

### 2. Upload video via dashboard
1. Open `http://localhost:3000`
2. Click "Upload Video for Analysis"
3. Select your test video
4. Wait for processing to complete

### 3. View results
- Alerts will appear in the dashboard
- Click on an alert to view detailed information
- Watch video clips showing the suspicious behavior

## Running Tests

### Backend tests
```bash
cd backend
pytest
```

### Frontend tests
```bash
cd frontend
npm test
```

## Troubleshooting

### YOLOv8 model download fails
The model will auto-download on first run. If it fails:
```bash
cd ml_models
mkdir -p ../ml_models
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Port already in use
Backend default port: 8000
Frontend default port: 3000

To change ports:
- Backend: Edit `PORT` in `.env`
- Frontend: Set `PORT=3001` before `npm start`

### CORS errors
Make sure the backend `.env` has:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Database errors
For SQLite (default), no setup needed. Database file will be created automatically.

For PostgreSQL:
1. Install PostgreSQL
2. Create database: `createdb theft_detection`
3. Update `DATABASE_URL` in `.env`

## Next Steps

1. **Add test videos** - Place videos showing different behaviors in `data/sample_videos/`
2. **Tune parameters** - Adjust suspicion score weights in `.env`
3. **Test detection** - Upload videos and verify alerts are generated correctly
4. **Review results** - Use the dashboard to review and classify alerts

## Architecture Overview

The system consists of 8 layers:
1. **Video Input Layer** - Processes video files
2. **Person Detection Layer** - YOLOv8 detects people
3. **Pose Estimation Layer** - MediaPipe tracks body pose
4. **Human-Object Interaction** - Analyzes hand movements
5. **Behavior Detection Engine** - Scores suspicious patterns
6. **Alert Generation** - Creates alerts with evidence
7. **Backend API** - FastAPI REST endpoints
8. **Web Dashboard** - React-based monitoring UI

## Performance Tips

- **Processing speed**: Adjust `VIDEO_PROCESSING_FPS` in `.env` (lower = faster, less accurate)
- **Detection sensitivity**: Adjust `SUSPICION_SCORE_THRESHOLD` in `.env` (lower = more alerts)
- **GPU acceleration**: Install CUDA-enabled PyTorch for faster processing

## Support

For issues or questions, check:
- Backend logs: Console output from `python -m app.main`
- Frontend logs: Browser developer console (F12)
- API documentation: `http://localhost:8000/docs`
