"""
Enrichment processor.
Runs ML models on queued files.
"""

import os
from db import get_connection
from scene_detect import detect_scenes
from clip_embed import embed_scenes_for_file
from whisper_transcribe import transcribe_video
from transcript_embed import embed_transcripts_for_file
from face_detect import detect_faces_for_file
from scanner import get_config


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
    return 1 + sum([
        models.get('clip', False), 
        models.get('whisper', False), 
        models.get('transcript_embed', False),
        models.get('arcface', False)
    ])


def process_file(file_id, video_path, job_id=None):
    """
    Run all enrichment steps on a video file.
    Respects model toggles from config.
    """
    filename = os.path.basename(video_path)
    print(f"\n  📁 {filename}")
    
    models = get_enabled_models()
    step = 0
    total_steps = get_total_stages(models)
    
    # Step 1: Scene detection (always runs)
    step += 1
    print(f"    [{step}/{total_steps}] Scene detection")
    if job_id:
        update_job_stage(job_id, 'scene_detection', step)
    detect_scenes(video_path, file_id)
    
    # Step 2: CLIP embeddings for each scene
    if models.get('clip', True):
        step += 1
        print(f"    [{step}/{total_steps}] CLIP embeddings")
        if job_id:
            update_job_stage(job_id, 'clip', step)
        embed_scenes_for_file(file_id)
    
    # Step 3: Whisper transcription
    if models.get('whisper', True):
        step += 1
        print(f"    [{step}/{total_steps}] Whisper transcription")
        if job_id:
            update_job_stage(job_id, 'whisper', step)
        transcribe_video(video_path, file_id)
    
    # Step 4: Transcript embeddings (semantic search)
    if models.get('transcript_embed', True):
        step += 1
        print(f"    [{step}/{total_steps}] Transcript embeddings")
        if job_id:
            update_job_stage(job_id, 'transcript_embed', step)
        embed_transcripts_for_file(file_id)
    
    # Step 5: ArcFace face detection
    if models.get('arcface', True):
        step += 1
        print(f"    [{step}/{total_steps}] Face detection")
        if job_id:
            update_job_stage(job_id, 'arcface', step)
        detect_faces_for_file(file_id)
    
    print("  ✅ Done")


def run_enrichment():
    """Process all pending enrichment jobs."""
    jobs = get_pending_jobs()
    
    if not jobs:
        return 0
    
    models = get_enabled_models()
    total_stages = get_total_stages(models)
    
    processed = 0
    for job_id, file_id, video_path in jobs:
        # Check if file still exists
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
    
    return processed
