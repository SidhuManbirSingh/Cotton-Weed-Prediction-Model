# Cotton Weed Detection System 🌱

## Project Overview
This project is an AI-powered web application that automatically detects weeds within cotton fields using drone or tractor footage. By accurately identifying weeds among crops, it empowers farmers to automate targeted herbicide spraying—significantly reducing manual labor costs, lowering chemical usage, and promoting healthier, more efficient agriculture.

## Why This Project Matters
Weed management is one of the most time-consuming and expensive challenges in modern agriculture. Traditional broadcast spraying wastes expensive chemicals and harms the environment. This system bridges the gap between raw field video and actionable intelligence. By processing footage to highlight exactly where weeds are located, it serves as the foundational software for smart-tractor automation, providing real-world value for sustainable farming.

## How It Works
The pipeline handles raw media files from start to finish seamlessly:
1. **Upload:** Users upload drone footage or field images via the React web interface.
2. **Frame Extraction:** The Flask backend splits continuous video into individual image frames.
3. **Model Inference:** A fine-tuned YOLOv8 model scans each frame to detect cotton plants and weeds simultaneously.
4. **Annotation:** Bounding boxes and confidence scores are drawn directly around detected targets.
5. **Video Reconstruction:** The annotated frames are instantly reassembled into a smooth output video.
6. **UI Display:** The frontend plays the original and processed media side-by-side for clear visual verification.

## Visual Results
> **Note to you:** Add your screenshots and GIFs below before submitting!
- **[Placeholder: Before & After Image]**
- **[Placeholder: Demo GIF showing side-by-side video play]**

## Features
- **Video & Image Processing:** Handles both static field photos and continuous drone video footage.
- **Real-time Style Pipeline:** Optimized file handling minimizes delay between upload and detection.
- **Side-by-Side Comparison UI:** Allows users to easily verify the model's accuracy against original footage.
- **Batch Processing Support:** Decoupled background threads process hundreds of frames without crashing or timing out.
- **Dockerized Deployment:** The entire system is containerized, meaning it runs consistently anywhere with a single command.
- **Optimized Inference:** Uses Intel OpenVINO to ensure the YOLO model runs incredibly fast, even without high-end cloud GPUs.

## Model Performance
The YOLOv8 model was fine-tuned on a custom dataset of annotated UAV imagery. It achieves strong separation between crop and weed classes.
* **mAP@50 (Weed):** 76.0%
* **Precision (Weed):** 74.9%
* **Recall (Weed):** 66.6%
* **mAP@50 (Cotton):** 93.8%

## Tech Stack
- **Frontend:** React, Vite, JavaScript, HTML, CSS
- **Backend:** Python, Flask, OpenCV
- **Machine Learning:** YOLOv8 (Ultralytics), PyTorch, Intel OpenVINO
- **Deployment:** Docker, Docker Compose, Bash Scripting

## Directory Structure
```text
Cotton-Weed-Prediction-Model/
 ├── backend/                 # Flask API, image processing, and inference logic
 ├── frontend/                # React user interface and design systems
 ├── training-the-model/      # Jupyter notebooks and data for training YOLOv8
 ├── utils/                   # Data science scripts for verifying dataset annotations
 ├── tools/                   # Developer scripts for testing and environment setup
 ├── samples/                 # Test images and video assets
 ├── docker-compose.yml       # Production deployment configuration
 ├── requirements.txt         # Global Python dependencies
 └── model.pt                 # The trained AI model weights
```

## Recommended Reading
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** — Core environment setup instructions.
- **`deployment_onboarding_guide.md`** — A beginner-friendly overview of the entire technology stack.
- **`technology_deep_dive.md`** — Detailed explanations on how React, Flask, Docker, and YOLO work under the hood.
- **`package_requirements_doc.md`** — A breakdown of all external packages utilized.
