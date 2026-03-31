#  Deployment and Usage Guide

This document outlines everything needed to set up, deploy, and run the **Inference of ML for Cotton-Weed Prediction** locally.

---

##  Prerequisites

Before proceeding, ensure you have the following installed on your host system:

- **Git** (to pull/track changes)
- **Node.js** (>= v20+ recommended)
- **Python** (>= 3.10+)
- **WSL (Windows Subsystem for Linux)** *(Highly recommended if deploying in Windows to align pipeline triggers correctly)*

---

##  1. Backend Setup & Start (Flask)

### **Step A: Set up Environment dependencies**
Start your WSL terminal to install required system modules and wrappers:

```bash
# Update local modules (Ignore if using global root access)
pip3 install flask flask-cors opencv-python-headless werkzeug ultralytics --break-system-packages
```

> [!NOTE]
> If using `venv`, do not use `--break-system-packages`. Simply run `pip install -r backend/requirements.txt` inside your activated environment.

### **Step B: Start the Server**
The project contains a quick start shell script that configures `PYTHONPATH`:

```bash
# Navigate to core workspace
cd /path/to/Cotton-Weed-Prediction-Model

# Run start script
bash start_backend.sh
```

The Flask handler will launch supporting queries on **`http://localhost:5000`**.

---

##  2. Frontend Setup & Start (Vite + React)

Open a **separate terminal window** to host serving packages for client rendering.

### **Step A: Install node packages**
```bash
cd frontend
npm install
```

### **Step B: Run interface in Dev Mode**
```bash
npm run dev
```

The app is now running on **`http://localhost:3000`**. 

Vite includes an automated rule forwarding any request starting with `/api` towards the core workspace indexer port: `5000`.

---

##  3. Testing Server Integrity 

To run a smoke mock payload verification to ensure frames are successfully writing with correct permissions without triggering front end client streams:

```bash
bash tools/test_backend.sh
```

---

##  Troubleshooting Guidelines

1. **Port Bind Failures (`5000` already bound)**: Some MacOS/Wine runtimes contain default services sitting on `5000`. You might need to change Flask wrapper headers in `server.py` to `5001` or superior mappings.
2. **Bounding Box Overlaps**: Adjust default Confidence payloads using the `--conf 0.35` multiplier on background API fetches. 
3. **Paths Unresolved**: The model weight `model.pt` must sit precisely on the **project root** directory level alongside `.git`.
