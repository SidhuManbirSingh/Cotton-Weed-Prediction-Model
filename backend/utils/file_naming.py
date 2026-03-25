import datetime

def generate_timestamp() -> str:
    """Generate a timestamp string in the format YYYYMMDD_HHMMSS."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def generate_frame_dir_name(timestamp: str) -> str:
    return f"frames_{timestamp}"

def generate_annotated_dir_name(timestamp: str) -> str:
    return f"annotated_{timestamp}"

def generate_output_video_name(timestamp: str) -> str:
    return f"output_{timestamp}.mp4"
