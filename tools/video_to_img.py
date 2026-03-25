import cv2
import os
import argparse
import hashlib

def frame_hash(frame):
    """Compute MD5 hash of a frame for duplicate detection."""
    _, buf = cv2.imencode('.jpg', frame)
    return hashlib.md5(buf.tobytes()).hexdigest()

def video_to_images(video_path, output_folder, frame_interval=1, skip_duplicates=False):
    """
    Extracts frames from a video and saves them as images.
    
    :param video_path: Path to the input video file.
    :param output_folder: Directory to save the extracted images.
    :param frame_interval: Extract one image every 'frame_interval' frames (e.g., 1 = every frame, 30 = every 30th frame).
    :param skip_duplicates: If True, skip frames that are identical to the previous saved frame.
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' not found.")
        return

    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video '{video_path}'.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Opened video: {video_path}")
    print(f"FPS: {fps:.2f}, Total frames: {total_frames}")
    print(f"Extracting every {frame_interval} frame(s)...")

    frame_count = 0
    saved_count = 0
    prev_hash = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Save the frame if it matches the requested interval
        if frame_count % frame_interval == 0:
            # Check for duplicate if enabled
            if skip_duplicates:
                curr_hash = frame_hash(frame)
                if prev_hash is not None and curr_hash == prev_hash:
                    # Skip this frame—identical to previous
                    frame_count += 1
                    continue
                prev_hash = curr_hash
            
            output_filename = os.path.join(output_folder, f"frame_{frame_count:06d}.jpg")
            cv2.imwrite(output_filename, frame)
            saved_count += 1
            if saved_count % 100 == 0:
                print(f"Saved {saved_count} images...")

        frame_count += 1

    cap.release()
    print(f"Done! Extracted {saved_count} images to '{output_folder}'.")

if __name__ == "__main__":
    # Configurable defaults
    DEFAULT_VIDEO = "project_video.mp4"
    DEFAULT_OUTPUTDIR = "extracted_images"
    DEFAULT_INTERVAL = 1  # 1 = extract every frame. 30 = extract every 30th frame.

    parser = argparse.ArgumentParser(description="Convert video to images by extracting frames.")
    parser.add_argument("--video", "-v", default=DEFAULT_VIDEO, help="Path to input video")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUTDIR, help="Output folder for the extracted images")
    parser.add_argument("--interval", "-i", type=int, default=DEFAULT_INTERVAL, help="Extract every N-th frame (e.g. 1 means all frames, 30 means 1 frame every 30 frames)")
    parser.add_argument("--skip-duplicates", action="store_true", help="Skip duplicate frames (identical to the previous one)")
    
    args = parser.parse_args()

    video_to_images(args.video, args.output, args.interval, skip_duplicates=args.skip_duplicates)
