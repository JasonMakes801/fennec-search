"""
Whisper transcription for dialog search.
Uses OpenAI Whisper (base model) for CPU inference.
"""

import whisper
import subprocess
import os
import tempfile
from db import get_connection
from progress import Spinner

# Global model (loaded once)
_model = None


def load_model():
    """Load Whisper model (base). Downloads on first run (~150MB)."""
    global _model
    
    if _model is not None:
        return _model
    
    print("    Loading Whisper model (first run downloads ~150MB)...")
    _model = whisper.load_model("base")
    print("    ✓ Whisper model loaded")
    
    return _model


def extract_audio(video_path, audio_path):
    """Extract audio from video using ffmpeg."""
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        audio_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=300)
        return os.path.exists(audio_path)
    except Exception as e:
        print(f"    ⚠️ Could not extract audio: {e}")
        return False


def transcribe_video(video_path, file_id):
    """
    Transcribe video audio and store segments in scenes.
    Returns number of segments transcribed.
    """
    # Check if file has audio tracks before attempting extraction
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT audio_tracks FROM files WHERE id = %s", (file_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result and result[0] == 0:
        print("    ⏭️  Skipping - no audio tracks")
        return 0
    
    model = load_model()
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        audio_path = f.name
    
    try:
        if not extract_audio(video_path, audio_path):
            print("    ⚠️ Audio extraction failed")
            return 0
        
        spinner = Spinner("Transcribing audio (takes ~1x video length)")
        spinner.start()
        
        result = model.transcribe(
            audio_path,
            language=None,
            word_timestamps=True,
            verbose=False
        )
        
        spinner.stop("Transcription complete")
        
        segments = result.get('segments', [])
        
        if not segments:
            print("    ⚠️ No speech detected")
            return 0
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, start_tc, end_tc 
            FROM scenes 
            WHERE file_id = %s 
            ORDER BY scene_index
        """, (file_id,))
        scenes = cur.fetchall()
        
        for scene_id, scene_start, scene_end in scenes:
            scene_text = []
            
            for seg in segments:
                seg_start = seg['start']
                seg_end = seg['end']
                
                if seg_start < scene_end and seg_end > scene_start:
                    scene_text.append(seg['text'].strip())
            
            if scene_text:
                transcript = ' '.join(scene_text)
                cur.execute(
                    "UPDATE scenes SET transcript = %s WHERE id = %s",
                    (transcript, scene_id)
                )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return len(segments)
        
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
