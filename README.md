# Inference of ML for Cotton-Weed Prediction

A clean, scalable AI-powered web application that processes video/image uploads to perform weed detection using YOLOv8, displaying a side-by-side comparison of original and AI-processed media.

---

##  Directory Structure

```text
Cotton-Weed-Prediction-Model/
 backend/                     # Python Flask API & Pipelines
    data/                    # Generated Assets & Uploads (Git-ignored content)
       annotated/           # Output directory for infernece-run frames
       frames/              # Extracted raw frames from uploaded videos
       output/              # Final processed MP4 files
       uploads/             # Raw uploaded images/videos
   
    scripts/                 # Core processing modular routines
       annotation.py        # Runs YOLOv8 inference on image directories
       convert.py           # Assembles annotated frames into slow-mo/regular MP4s
       video2image.py       # Decodes videos into frame-by-frame JPGs
   
    utils/                   # Shared pipeline utilities
       file_naming.py       # Timestamp generators for folder & file parity
       path_manager.py      # Central location handling absolute paths 
   
    server/                  # REST API Layer
        server.py            # Main Flask app with background jobs & static streams

 frontend/                    # Vite + React Front-end Interface
    src/
       App.jsx              # Main dashboard component logic
       index.css            # Dark mode design tokens & glassmorphism framework
       main.jsx             # React DOM entry point
    package.json             # JS Dependencies 
    vite.config.js           # Includes port forwarding or API proxies

 model.pt                     # Loaded weights for YOLO detections (Required)
 tools/                   # Developer utilities & test scripts
    check_deps.sh        # Verify WSL environment & Python dependencies
    check_model.sh       # Validate OpenVINO model integrity
    run_batch_inference.py # Template for local bulk image processing
    test_backend.sh      # CLI tool to smoke-test API endpoints
    test_image_inference.sh # Validates the single-image AI pipeline
    video_to_img.py      # Standalone frame extraction utility

 samples/                 # Large media assets for development
    project_video.mp4    # Main test footage (high-bitrate)
    project-video-short.mp4 # Short-form testing clip

 start_backend.sh         # Launch wrapper for Flask server runs
```

##  Key System Pillars

1. **Safety & Speed Control**: Path Management utilities use purely isolated node streams making batch rewrites scalable to multiple processors or remote cloud buckets without mutating baseline assets.
2. **Side-by-Side Visualization UI**: Dynamic overlays allowing visual inspection on whether prediction is properly thresholded inside image bounding wrappers.
3. **Queue Processing Handler**: Decoupled thread pooling executes frame decomposition so larger videos do not timeout client requests.

---

Refer to [DEPLOYMENT.md](./DEPLOYMENT.md) for setup instructions.
