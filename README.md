# Inference of ML for Cotton-Weed Prediction

A clean, scalable AI-powered web and operational pipeline that processes video/image uploads to perform weed detection using **YOLOv8**, displaying a side-by-side comparison of original and AI-processed media.

Powered by a modern tech stack encompassing **React/Vite** on the frontend, **Flask/OpenVINO** on the backend, and **PyTorch** for model training optimization.

---

## 📁 Directory Structure

```text
Cotton-Weed-Prediction-Model/
 ├── backend/                 # Python Flask API & Pipelines
 │    ├── data/               # Generated Assets & Uploads (Git-ignored)
 │    │   ├── annotated/      # Output directory for inference-run frames
 │    │   ├── frames/         # Extracted raw frames from uploaded videos
 │    │   ├── output/         # Final processed MP4 files
 │    │   └── uploads/        # Raw uploaded images/videos
 │    ├── scripts/            # Core processing modular routines
 │    │   ├── annotation.py   # Runs YOLOv8 inference on image directories
 │    │   ├── convert.py      # Assembles annotated frames into MP4s
 │    │   └── video2image.py  # Decodes videos into frame-by-frame JPGs
 │    ├── utils/              # Shared pipeline utilities
 │    │   ├── file_naming.py  # Timestamp generators for folder & file parity
 │    │   └── path_manager.py # Central location handling absolute paths 
 │    └── server/             # REST API Layer
 │        └── server.py       # Main Flask app with background jobs
 │
 ├── frontend/                # Vite + React Front-end Interface
 │    ├── src/
 │    │   ├── App.jsx         # Main dashboard component logic
 │    │   ├── index.css       # Dark mode design tokens & styling
 │    │   └── main.jsx        # React DOM entry point
 │    ├── package.json        # JS Dependencies 
 │    └── vite.config.js      # Build config & API proxies
 │
 ├── training-the-model/      # Core AI Data Science & Training Notebooks
 │    ├── Weed_Detection_Model.ipynb # YOLOv8 fine-tuning pipeline
 │    └── data.yaml           # YOLO data configuration mapping
 │
 ├── utils/                   # ML Dataset Operations & Data Science Tooling
 │    ├── dataset_stats.py           # Counts & tabularizes YOLO class distributions
 │    ├── dataset_visualizer.py      # Visually verifies YOLO boundary boxes
 │    └── dataset_annotation_dump.py # CLI output for annotation text validation
 │
 ├── tools/                   # Developer utilities & test scripts
 │    ├── check_deps.sh       # Verify WSL environment & Python dependencies
 │    ├── check_model.sh      # Validate OpenVINO model integrity
 │    ├── run_batch_inference.py # Template for local bulk image processing
 │    ├── test_backend.sh     # CLI tool to smoke-test API endpoints
 │    ├── test_image_inference.sh # Validates the single-image AI pipeline
 │    └── video_to_img.py     # Standalone frame extraction utility
 │
 ├── samples/                 # Large media assets for development
 │    ├── project_video.mp4       # Main test footage (high-bitrate)
 │    └── project-video-short.mp4 # Short-form testing clip
 │
 ├── requirements.txt         # Global Python dependencies (Flask, Ultralytics, PyTorch)
 ├── docker-compose.yml       # Production orchestration logic
 ├── deployment-script.sh     # Seamless environment startup script
 ├── start_backend.sh         # Launch wrapper for Flask server runs
 └── model.pt                 # Optimized weights for live YOLO detections
```

## ⚡ Key System Pillars

1. **Safety & Speed Control**: Path Management utilities use purely isolated node streams making batch rewrites scalable to multiple processors without mutating baseline assets.
2. **Side-by-Side Visualization UI**: Dynamic overlays allowing visual inspection on whether prediction is properly thresholded inside image bounding wrappers.
3. **Queue Processing Handler**: Decoupled thread pooling executes frame decomposition so larger videos do not timeout client requests.
4. **End-to-End AI Integration**: Complete visibility from raw data bounding mapping (`Weed_Detection_Model.ipynb`), to dataset verification (`utils/`), directly into hardware-accelerated predictions (OpenVINO).

---

## 📖 Recommended Reading
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** — Core environment setup instructions.
- **`deployment_onboarding_guide.md`** — For a beginner-friendly overview of the entire underlying technology stack.
- **`technology_deep_dive.md`** — For detailed explanations on how React, Flask, Docker, and YOLO work fundamentally under the hood.
- **`package_requirements_doc.md`** — For an explicit breakdown of all external node/python packages utilized.
