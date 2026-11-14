# CottonVision: UAV Cotton and Weed Detection System

AI-powered computer vision system for detecting weeds in cotton fields from UAV aerial imagery and orthomosaics, enabling targeted precision spraying and reduced chemical waste.

[![Watch Demo on YouTube](https://img.shields.io/badge/Demo-YouTube-red?logo=youtube)](https://youtu.be/bO3l2jyvdKA)
[![Model YOLOv8](https://img.shields.io/badge/Model-YOLOv8-blue)](https://github.com/ultralytics/ultralytics)
[![Intel OpenVINO](https://img.shields.io/badge/Runtime-OpenVINO-cyan)](https://docs.openvino.ai/)
[![Dataset](https://img.shields.io/badge/Dataset-Google%20Drive-green)](https://drive.google.com/drive/folders/1rnBnCmXL_B9jeZK325pCOdOYbs2EzgAg?usp=sharing)
[![License](https://img.shields.io/badge/License-Apache--2.0-yellow)](./LICENSE)

---

## Quick Start

Launch the application (backend inference API and web interface) with a single command:

**Linux / macOS / WSL / Git Bash:**
```bash
bash deployment-script.sh
```

**Windows (Command Prompt / PowerShell):**
```cmd
run.bat
```

*Or run the server directly with Python:*
```bash
python -m backend.server.server
```

Once running, access the application at **http://localhost:5000**.

If Node.js and npm are installed, the Vite development frontend can optionally be started on **http://localhost:3000** (`cd frontend && npm run dev`).

---

## Visual Demonstration

* **Video Walkthrough**: [Watch on YouTube](https://youtu.be/bO3l2jyvdKA)
* **Live Inference**:

![Demo GIF](./assets/demo.gif)

* **Detection Output (Original UAV Stream vs Annotated Detection)**:

![Before and After Detection](./assets/before_after.png)

---

## Key Features

* **Landing Page & Workbench Interface**: Complete web application featuring Host Grotesk typography, responsive layout, and side-by-side aerial stream inspection.
* **Dual-Path UAV Media Pipeline**: Sub-second single-shot inference for high-resolution orthomosaics alongside asynchronous background processing for 4K drone flight videos.
* **Temporal-Locked Frame Skipping**: Eliminates speed distortion by dynamically calculating output frame rates:
  $$\text{Output FPS} = \frac{\text{Source FPS}}{\text{Frame Interval}}$$
  Intervals (1x, 2x, 5x, 10x, 15x) maintain true flight duration.
* **Browser-Native H.264 Video**: Transcodes output with the `avc1` codec and fast-start metadata for immediate HTML5 playback.
* **YOLO Dataset Export**: Exports extracted frames and normalized YOLOv8 labels (`.txt`) in a structured `.zip` archive for model fine-tuning and sprayer navigation.
* **Hardware Acceleration**: CPU and Intel Arc GPU support via Intel OpenVINO.

---

## Model Performance

Evaluated on high-resolution UAV aerial datasets under varying field and illumination conditions:

| Metric | Weed Detection | Cotton Crop Detection |
| :--- | :--- | :--- |
| **mAP@50** | **76.0%** | **93.8%** |
| **Precision** | **74.9%** | **91.2%** |
| **Recall** | **66.6%** | **89.5%** |
| **Runtime** | YOLOv8 + OpenVINO | YOLOv8 + OpenVINO |

---

## Dataset

The annotated UAV aerial image dataset used to train the YOLOv8 model is publicly available:

* **[Download Cotton-Weed UAV Dataset (Google Drive)](https://drive.google.com/drive/folders/1rnBnCmXL_B9jeZK325pCOdOYbs2EzgAg?usp=sharing)**

---

## Technology Stack

* **Frontend**: React 19, Vite, Host Grotesk Web Font, HTML5, CSS3.
* **Backend**: Python 3.10+, Flask, Flask-CORS, Werkzeug.
* **Machine Learning**: YOLOv8 (Ultralytics), PyTorch, Intel OpenVINO, OpenCV.
* **Deployment**: Shell (`deployment-script.sh`), Batch (`run.bat`), Docker.

---

## Project Structure

```text
Cotton-Weed-Prediction-Model/
 ├── index.html              # Standalone web application
 ├── deployment-script.sh    # Single-command launcher (Unix/WSL)
 ├── run.bat                 # Single-command launcher (Windows)
 ├── start_backend.sh        # Backend startup script
 ├── model.pt                # Trained YOLOv8 model weights
 ├── requirements.txt        # Python dependencies
 ├── docker-compose.yml      # Container orchestration
 ├── assets/                 # Demonstration media and figures
 ├── backend/
 │    ├── server/            # Flask REST API and static route handlers
 │    ├── scripts/           # Video extraction, annotation, and transcoding
 │    └── utils/             # Path management and timestamp utilities
 ├── frontend/               # React Vite source code and styles
 ├── samples/                # Sample aerial imagery for testing
 ├── training-the-model/     # Training notebooks and validation metrics
 └── utils/                  # Dataset analysis and visualization scripts
```

---

## API Reference

The Flask backend exposes the following endpoints on port `5000`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the web interface and workbench |
| `POST` | `/api/upload` | Uploads aerial image or video files |
| `POST` | `/api/process-image` | Runs single-image inference and returns annotations |
| `POST` | `/api/process` | Enqueues video frame extraction and inference pipeline |
| `GET` | `/api/status/<job_id>` | Returns processing state, frame count, and progress |
| `GET` | `/api/media/<path>` | Serves raw and annotated media files |
| `GET` | `/api/download/dataset/<job_id>` | Generates and downloads paired YOLO dataset archive (.zip) |

---

## Documentation

* **[DEPLOYMENT.md](./DEPLOYMENT.md)**: Setup, virtual environment, and system prerequisites.
* **[Challenges_and_Solutions.md](./Challenges_and_Solutions.md)**: Engineering analysis on codecs, frame timing, and pipelines.
* **[Final_Report.pdf](./Final_Report.pdf)**: Research methodology and agronomic evaluation.

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.
