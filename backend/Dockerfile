# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies required for OpenCV and video processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to the project root 
# (This matches the assumption of PYTHONPATH and relative paths in the code)
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy the backend requirements file and install dependencies
# We do this before copying the rest of the code to cache the dependencies layer
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the backend source code and the model file
COPY backend/ /app/backend/
COPY model.pt /app/

# Set the Python path to include the /app directory
ENV PYTHONPATH=/app

# Expose the Flask port
EXPOSE 5000

# Start the Flask development server on all interfaces
CMD ["python", "-m", "backend.server.server"]
