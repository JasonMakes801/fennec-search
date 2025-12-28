"""
Scene detection using PySceneDetect.
Detects scene cuts and extracts poster frames.
"""

import os
import subprocess
from scenedetect import detect, ContentDetector, AdaptiveDetector
from db import get_connection
from progress import Spinner, progress_counter, progress_done
from scanner import get_config

# Where to store extracted poster frames
POSTER_DIR = "/app/posters"


def get_poster_settings():
    """Get poster frame settings from config."""
    return {
        'width': get_config('poster_width', 1280),       # 720p width
        'format': get_config('poster_format', 'webp'),
        'quality': get_config('poster_quality', 80)
    }


def ensure_poster_dir():
    """Create poster directory if it doesn't exist."""
    os.makedirs(POSTER_DIR, exist_ok=True)


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"    ⚠️  Could not get duration: {e}")
        return None


def get_video_fps(video_path):
    """Get video frame rate using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # r_frame_rate returns as fraction like "24000/1001" or "24/1"
        fps_str = result.stdout.strip()
        if '/' in fps_str:
            num, den = fps_str.split('/')
            return float(num) / float(den)
        return float(fps_str)
    except Exception as e:
        print(f"    ⚠️  Could not get FPS, defaulting to 24: {e}")
        return 24.0


def extract_frame(video_path, timecode, output_path, width=1280, quality=80):
    """
    Extract a single frame at the given timecode using ffmpeg.
    Scales to specified width (maintaining aspect ratio) and outputs WebP.
    """
    # Determine format from extension
    _, ext = os.path.splitext(output_path)
    
    # Build filter for scaling (maintain aspect ratio)
    scale_filter = f"scale={width}:-2"  # -2 ensures even height
    
    # Quality settings vary by format
    if ext.lower() == '.webp':
        quality_args = ['-quality', str(quality)]
    else:
        quality_args = ['-q:v', '2']  # JPG quality
    
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(timecode),
        '-i', video_path,
        '-frames:v', '1',
        '-vf', scale_filter,
        *quality_args,
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=30)
        return os.path.exists(output_path)
    except Exception as e:
        print(f"    ⚠️  Could not extract frame: {e}")
        return False


def detect_scenes(video_path, file_id):
    """
    Detect scenes in a video and save to database.
    Returns number of scenes detected.
    """
    ensure_poster_dir()
    
    # Get poster settings
    poster_settings = get_poster_settings()
    poster_width = poster_settings['width']
    poster_format = poster_settings['format']
    poster_quality = poster_settings['quality']
    poster_ext = f".{poster_format}"
    
    print(f"    Detecting scenes...")
    
    # Use ContentDetector for scene changes
    # threshold=27 is default, lower = more sensitive
    scene_list = detect(video_path, ContentDetector(threshold=27))
    
    # Get FPS to calculate one frame duration (for avoiding overlap)
    fps = get_video_fps(video_path)
    frame_duration = 1.0 / fps
    
    # If no scenes detected, treat whole video as one scene
    if not scene_list:
        duration = get_video_duration(video_path)
        if duration:
            scene_list = [(0, duration)]
        else:
            scene_list = [(0, 0)]  # Fallback
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Clear existing scenes for this file (in case of re-processing)
    cur.execute("DELETE FROM scenes WHERE file_id = %s", (file_id,))
    
    total = len(scene_list)
    for i, scene in enumerate(scene_list):
        progress_counter(i + 1, total, "Extracting frames")
        # scene is a tuple of (start_time, end_time) or FrameTimecode objects
        if hasattr(scene[0], 'get_seconds'):
            start_tc = scene[0].get_seconds()
            end_tc = scene[1].get_seconds()
        else:
            start_tc = float(scene[0])
            end_tc = float(scene[1])
        
        # Extract CENTER frame (for thumbnails, CLIP embedding, and player initial display)
        mid_tc = (start_tc + end_tc - frame_duration) / 2
        mid_filename = f"{file_id}_{i:04d}{poster_ext}"
        mid_path = os.path.join(POSTER_DIR, mid_filename)
        
        if extract_frame(video_path, mid_tc, mid_path, poster_width, poster_quality):
            poster_db_path = mid_path
        else:
            poster_db_path = None
        
        # Insert scene into database
        cur.execute(
            """
            INSERT INTO scenes (file_id, scene_index, start_tc, end_tc, poster_frame_path)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (file_id, i, start_tc, end_tc, poster_db_path)
        )
    
    conn.commit()
    cur.close()
    conn.close()
    
    progress_done(f"{total} scenes detected")
    return total
