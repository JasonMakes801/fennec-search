"""
Enrichment processor.
Runs ML models on queued files.

Note: FFprobe metadata extraction now happens here (deferred from scan phase)
to keep scans instant. If FFprobe fails, the job is marked as failed.
"""

import os
from db import get_connection
from scene_detect import detect_scenes
from clip_embed import embed_scenes_for_file
from whisper_transcribe import transcribe_video
from transcript_embed import embed_transcripts_for_file
from face_detect import detect_faces_for_file
from scanner import get_config, get_video_metadata, get_watch_folders


def get_enabled_models():
    """Get which models are enabled from config."""
    default = {'clip': True, 'whisper': True, 'transcript_embed': True, 'arcface': True}
    return get_config('enrichment_models', default)


def get_pending_jobs(limit=10):
    """Get pending enrichment jobs."""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT eq.id, eq.file_id, f.path
        FROM enrichment_queue eq
        JOIN files f ON f.id = eq.file_id
        WHERE eq.status = 'pending'
        ORDER BY eq.queued_at
        LIMIT %s
    """, (limit,))
    
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    
    return jobs


def mark_job_processing(job_id, total_stages):
    """Mark a job as processing with total stage count."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE enrichment_queue 
        SET status = 'processing', started_at = NOW(),
            current_stage = 'starting', current_stage_num = 0, total_stages = %s
        WHERE id = %s
    """, (total_stages, job_id))
    conn.commit()
    cur.close()
    conn.close()


def update_job_stage(job_id, stage_name, stage_num):
    """Update the current stage of a processing job."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE enrichment_queue 
        SET current_stage = %s, current_stage_num = %s
        WHERE id = %s
    """, (stage_name, stage_num, job_id))
    conn.commit()
    cur.close()
    conn.close()


def mark_job_complete(job_id):
    """Mark a job as complete and update file indexed_at."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Mark queue job complete
    cur.execute("""
        UPDATE enrichment_queue 
        SET status = 'complete', completed_at = NOW()
        WHERE id = %s
    """, (job_id,))
    
    # Update file's indexed_at timestamp
    cur.execute("""
        UPDATE files 
        SET indexed_at = NOW()
        WHERE id = (SELECT file_id FROM enrichment_queue WHERE id = %s)
    """, (job_id,))
    
    conn.commit()
    cur.close()
    conn.close()


def mark_job_failed(job_id, error):
    """Mark a job as failed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE enrichment_queue 
        SET status = 'failed', error = %s, retry_count = retry_count + 1
        WHERE id = %s
    """, (error, job_id))
    conn.commit()
    cur.close()
    conn.close()


def get_total_stages(models):
    """Calculate total stages based on enabled models."""
    # +1 for scene detection, +1 for metadata extraction (if needed)
    return 2 + sum([
        models.get('clip', False),
        models.get('whisper', False),
        models.get('transcript_embed', False),
        models.get('arcface', False)
    ])


def extract_metadata_if_needed(file_id, video_path):
    """
    Extract video metadata with FFprobe if not already present.
    This is called during enrichment for files where probe was deferred during scan.

    Returns True if metadata is valid, False if file is unreadable.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Check if we already have metadata
    cur.execute("SELECT duration_seconds FROM files WHERE id = %s", (file_id,))
    row = cur.fetchone()

    if row and row[0] is not None:
        # Already have duration, metadata was extracted during scan
        cur.close()
        conn.close()
        return True

    # Extract metadata with FFprobe
    print(f"    Extracting video metadata...")
    video_meta = get_video_metadata(video_path)

    # Check if FFprobe succeeded
    if video_meta['duration_seconds'] is None:
        cur.close()
        conn.close()
        return False  # Unreadable file

    # Update file record with metadata
    cur.execute("""
        UPDATE files SET
            duration_seconds = %s,
            width = %s,
            height = %s,
            fps = %s,
            codec = %s,
            audio_tracks = %s,
            pix_fmt = %s,
            color_space = %s,
            color_transfer = %s,
            color_primaries = %s
        WHERE id = %s
    """, (
        video_meta['duration_seconds'],
        video_meta['width'],
        video_meta['height'],
        video_meta['fps'],
        video_meta['codec'],
        video_meta['audio_tracks'],
        video_meta['pix_fmt'],
        video_meta['color_space'],
        video_meta['color_transfer'],
        video_meta['color_primaries'],
        file_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    return True


def process_file(file_id, video_path, job_id=None):
    """
    Run all enrichment steps on a video file.
    Respects model toggles from config.

    Raises ValueError if metadata extraction fails (unreadable file).
    """
    filename = os.path.basename(video_path)
    print(f"\n  📁 {filename}")

    models = get_enabled_models()
    step = 0
    total_steps = get_total_stages(models)

    # Step 1: Extract metadata if needed (deferred from scan phase)
    step += 1
    print(f"    [{step}/{total_steps}] Metadata extraction")
    if job_id:
        update_job_stage(job_id, 'metadata', step)

    if not extract_metadata_if_needed(file_id, video_path):
        raise ValueError(f"FFprobe failed - file may be corrupted or unsupported format")

    # Step 2: Scene detection (always runs)
    step += 1
    print(f"    [{step}/{total_steps}] Scene detection")
    if job_id:
        update_job_stage(job_id, 'scene_detection', step)
    detect_scenes(video_path, file_id)
    
    # Step 3: CLIP embeddings for each scene
    if models.get('clip', True):
        step += 1
        print(f"    [{step}/{total_steps}] CLIP embeddings")
        if job_id:
            update_job_stage(job_id, 'clip', step)
        embed_scenes_for_file(file_id)

    # Step 4: Whisper transcription
    if models.get('whisper', True):
        step += 1
        print(f"    [{step}/{total_steps}] Whisper transcription")
        if job_id:
            update_job_stage(job_id, 'whisper', step)
        transcribe_video(video_path, file_id)

    # Step 5: Transcript embeddings (semantic search)
    if models.get('transcript_embed', True):
        step += 1
        print(f"    [{step}/{total_steps}] Transcript embeddings")
        if job_id:
            update_job_stage(job_id, 'transcript_embed', step)
        embed_transcripts_for_file(file_id)

    # Step 6: ArcFace face detection
    if models.get('arcface', True):
        step += 1
        print(f"    [{step}/{total_steps}] Face detection")
        if job_id:
            update_job_stage(job_id, 'arcface', step)
        detect_faces_for_file(file_id)
    
    print("  ✅ Done")


def get_accessible_watch_folders():
    """
    Get list of watch folders that are currently accessible.
    Used to avoid marking files as failed when their parent folder is just unmounted.
    """
    watch_folders = get_watch_folders()
    return [f for f in watch_folders if os.path.isdir(f)]


def is_in_accessible_folder(video_path, accessible_folders):
    """Check if a video path is under an accessible watch folder."""
    return any(video_path.startswith(folder) for folder in accessible_folders)


def run_enrichment():
    """Process all pending enrichment jobs."""
    jobs = get_pending_jobs()

    if not jobs:
        return 0

    models = get_enabled_models()
    total_stages = get_total_stages(models)

    # Determine which watch folders are accessible
    accessible_folders = get_accessible_watch_folders()

    processed = 0
    skipped_unmounted = 0
    for job_id, file_id, video_path in jobs:
        # Check if file's watch folder is accessible
        if not is_in_accessible_folder(video_path, accessible_folders):
            # Watch folder is unmounted - skip without marking failed
            skipped_unmounted += 1
            continue

        # Watch folder is accessible but file is missing - this is a real problem
        if not os.path.exists(video_path):
            print(f"    ⚠️  File not found: {video_path}")
            mark_job_failed(job_id, "File not found")
            continue

        mark_job_processing(job_id, total_stages)
        
        try:
            process_file(file_id, video_path, job_id)
            mark_job_complete(job_id)
            processed += 1
        except Exception as e:
            print(f"    ❌ Error: {e}")
            mark_job_failed(job_id, str(e))

    if skipped_unmounted > 0:
        print(f"  ⏸️  Skipped {skipped_unmounted} files in unmounted watch folders")

    return processed
