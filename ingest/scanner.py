"""
File scanner for the ingest service.
Scans watch folders for video files and adds them to the database.
Uses polling (no watchdog) for NFS/SMB compatibility.

Performance notes:
- Uses os.scandir() instead of os.walk() for faster directory traversal
- FFprobe metadata extraction is deferred to enrichment phase for instant scans
- Progress is written to DB for Reports UI visibility
"""

import os
import subprocess
import json
import logging
from datetime import datetime
from db import get_connection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)


# Supported video extensions
# Only formats FFmpeg can fully decode (not just demux)
# Excludes: R3D (RED), BRAW (Blackmagic), ARI (ARRI) - require proprietary SDKs
VIDEO_EXTENSIONS = {
    '.mp4', '.mov', '.m4v', '.3gp', '.3g2',  # QuickTime/MP4
    '.avi',                                   # AVI
    '.mkv', '.webm',                          # Matroska
    '.mxf',                                   # MXF (broadcast)
    '.wmv', '.asf',                           # Windows Media
    '.flv',                                   # Flash Video
    '.ts', '.m2ts', '.mts',                   # MPEG Transport Stream
    '.mpg', '.mpeg', '.vob',                  # MPEG Program Stream
    '.ogv',                                   # Ogg Video
    '.rm', '.rmvb',                           # RealMedia
    '.wtv',                                   # Windows TV
    '.dv',                                    # DV
    '.mj2',                                   # Motion JPEG 2000
    '.bik', '.bk2',                           # Bink Video
}


def get_video_extensions():
    """Return set of supported video file extensions."""
    return VIDEO_EXTENSIONS


def get_config(key, default=None):
    """Get a config value from the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = %s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row is None:
        return default
    return row[0]


def set_config(key, value):
    """Set a config value in the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO config (key, value) 
        VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (key, json.dumps(value)))
    conn.commit()
    cur.close()
    conn.close()


def get_watch_folders():
    """Get list of watch folders from config table."""
    return get_config('watch_folders', [])


def get_indexer_state():
    """Get current indexer state (running/paused)."""
    return get_config('indexer_state', 'running')


def get_poll_interval():
    """Get poll interval in seconds."""
    return get_config('poll_interval_seconds', 3600)


# ============ Scan Progress Tracking ============

def update_scan_progress(phase, current_folder=None, dirs_scanned=0, files_found=0,
                         files_processed=0, files_new=0, files_updated=0, files_skipped=0):
    """
    Update scan progress in config table for UI visibility.
    This allows the Reports page to show what the scanner is doing.
    """
    progress = {
        'phase': phase,  # 'discovering', 'processing', 'checking_missing', 'complete', 'idle'
        'current_folder': current_folder,
        'dirs_scanned': dirs_scanned,
        'files_found': files_found,
        'files_processed': files_processed,
        'files_new': files_new,
        'files_updated': files_updated,
        'files_skipped': files_skipped,
        'updated_at': datetime.now().isoformat()
    }
    set_config('scan_progress', progress)


def clear_scan_progress():
    """Clear scan progress (set to idle state)."""
    update_scan_progress('idle')


def get_scan_progress():
    """Get current scan progress."""
    return get_config('scan_progress', {'phase': 'idle'})


def is_video_file(path):
    """Check if a file is a video based on extension."""
    _, ext = os.path.splitext(path)
    return ext.lower() in get_video_extensions()


def get_video_metadata(video_path):
    """
    Extract video metadata using FFprobe.
    Returns dict with: duration, width, height, fps, codec, audio_tracks, color info
    """
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate,codec_name,pix_fmt,color_space,color_transfer,color_primaries',
        '-show_entries', 'format=duration',
        '-of', 'json',
        video_path
    ]
    
    metadata = {
        'duration_seconds': None,
        'width': None,
        'height': None,
        'fps': None,
        'codec': None,
        'audio_tracks': 0,
        'pix_fmt': None,
        'color_space': None,
        'color_transfer': None,
        'color_primaries': None
    }
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        
        # Get format-level info
        if 'format' in data and 'duration' in data['format']:
            metadata['duration_seconds'] = float(data['format']['duration'])
        
        # Get stream info
        if 'streams' in data and len(data['streams']) > 0:
            stream = data['streams'][0]
            metadata['width'] = stream.get('width')
            metadata['height'] = stream.get('height')
            metadata['codec'] = stream.get('codec_name')
            
            # Parse frame rate (usually comes as "30000/1001" or "30/1")
            if 'r_frame_rate' in stream:
                fps_str = stream['r_frame_rate']
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    if int(den) > 0:
                        metadata['fps'] = round(int(num) / int(den), 3)
            
            # Color metadata
            metadata['pix_fmt'] = stream.get('pix_fmt')
            metadata['color_space'] = stream.get('color_space')
            metadata['color_transfer'] = stream.get('color_transfer')
            metadata['color_primaries'] = stream.get('color_primaries')
        
        # Count audio tracks
        audio_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=index',
            '-of', 'csv=p=0',
            video_path
        ]
        audio_result = subprocess.run(audio_cmd, capture_output=True, text=True, timeout=30)
        if audio_result.stdout.strip():
            metadata['audio_tracks'] = len(audio_result.stdout.strip().split('\n'))
            
    except Exception as e:
        print(f"    ⚠️  Could not extract metadata: {e}")
    
    return metadata


def get_file_metadata(filepath):
    """
    Extract filesystem metadata.
    Returns dict with: file_size_bytes, file_created_at, file_modified_at, parent_folder
    """
    metadata = {
        'file_size_bytes': None,
        'file_created_at': None,
        'file_modified_at': None,
        'parent_folder': None
    }
    
    try:
        stat = os.stat(filepath)
        metadata['file_size_bytes'] = stat.st_size
        metadata['file_modified_at'] = datetime.fromtimestamp(stat.st_mtime)
        
        # st_birthtime is macOS, st_ctime is creation on Windows, modified on Linux
        if hasattr(stat, 'st_birthtime'):
            metadata['file_created_at'] = datetime.fromtimestamp(stat.st_birthtime)
        else:
            metadata['file_created_at'] = datetime.fromtimestamp(stat.st_ctime)
        
        # Parent folder name (just the immediate directory)
        metadata['parent_folder'] = os.path.basename(os.path.dirname(filepath))
        
    except Exception as e:
        print(f"    ⚠️  Could not extract file metadata: {e}")
    
    return metadata


def scan_folder(folder_path, on_progress=None):
    """
    Scan a folder recursively for video files using os.scandir (faster than os.walk).
    Returns list of absolute paths.

    Args:
        folder_path: Root folder to scan
        on_progress: Optional callback(dirs_scanned, current_dir) for progress updates
    """
    videos = []
    dirs_scanned = 0

    if not os.path.exists(folder_path):
        print(f"  ⚠️  Folder not found: {folder_path}")
        logger.warning(f"Folder not found: {folder_path}")
        return videos

    def _scan_recursive(path):
        nonlocal dirs_scanned
        try:
            with os.scandir(path) as entries:
                dirs_scanned += 1
                subdirs = []

                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            subdirs.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            if is_video_file(entry.name):
                                videos.append(entry.path)
                    except (PermissionError, OSError):
                        continue

                # Log progress every 100 directories
                if dirs_scanned % 100 == 0:
                    logger.info(f"Scanned {dirs_scanned} directories, found {len(videos)} videos so far...")
                    if on_progress:
                        on_progress(dirs_scanned, path)

                # Recurse into subdirectories
                for subdir in subdirs:
                    _scan_recursive(subdir)

        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot access {path}: {e}")

    _scan_recursive(folder_path)
    logger.info(f"Scan complete: {dirs_scanned} directories, {len(videos)} videos found")

    return videos


def add_file_to_db(filepath, defer_probe=True):
    """
    Add a video file to the database if it doesn't exist,
    or re-queue if the file has been modified since last indexing.

    Args:
        filepath: Path to video file
        defer_probe: If True (default), skip FFprobe during scan - metadata will be
                     extracted during enrichment phase. This makes scans instant.

    Returns (file_id, is_new, was_updated).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Get current file's modified time and size (fast - no FFprobe)
    current_mtime = None
    current_size = None
    try:
        stat = os.stat(filepath)
        current_mtime = datetime.fromtimestamp(stat.st_mtime)
        current_size = stat.st_size
    except Exception as e:
        logger.warning(f"Cannot stat file {filepath}: {e}")
        cur.close()
        conn.close()
        return None, False, False

    # Check if file already exists
    cur.execute("SELECT id, deleted_at, file_modified_at, file_size_bytes, indexed_at FROM files WHERE path = %s", (filepath,))
    existing = cur.fetchone()

    if existing:
        file_id, deleted_at, db_mtime, db_size, indexed_at = existing

        if deleted_at is not None:
            # File was soft-deleted but reappeared - resurrect it
            logger.info(f"Resurrecting previously deleted file: {filepath}")
            cur.execute("UPDATE files SET deleted_at = NULL WHERE id = %s", (file_id,))
            conn.commit()
            cur.close()
            conn.close()
            return file_id, True, False  # Treat as new for re-enrichment

        # Check if file has been modified since last indexing
        # Use both mtime and size for faster detection
        file_changed = False
        if indexed_at is not None and current_mtime is not None and db_mtime is not None:
            # Compare timestamps (allow 1 second tolerance for filesystem precision)
            if current_mtime > db_mtime and (current_mtime - db_mtime).total_seconds() > 1:
                file_changed = True
            # Also check size - quick way to detect changes
            if current_size is not None and db_size is not None and current_size != db_size:
                file_changed = True

        if file_changed:
            logger.info(f"File modified, re-queuing: {filepath}")
            # File was modified - update basic metadata and re-queue
            # FFprobe will run during enrichment if defer_probe=True
            file_meta = get_file_metadata(filepath)

            if defer_probe:
                # Just update file metadata, FFprobe runs during enrichment
                cur.execute("""
                    UPDATE files SET
                        file_modified_at = %s,
                        file_size_bytes = %s,
                        indexed_at = NULL,
                        duration_seconds = NULL,
                        width = NULL,
                        height = NULL,
                        fps = NULL,
                        codec = NULL,
                        audio_tracks = NULL
                    WHERE id = %s
                """, (file_meta['file_modified_at'], file_meta['file_size_bytes'], file_id))
            else:
                video_meta = get_video_metadata(filepath)
                cur.execute("""
                    UPDATE files SET
                        file_modified_at = %s,
                        file_size_bytes = %s,
                        duration_seconds = %s,
                        width = %s,
                        height = %s,
                        fps = %s,
                        codec = %s,
                        audio_tracks = %s,
                        indexed_at = NULL
                    WHERE id = %s
                """, (
                    file_meta['file_modified_at'],
                    file_meta['file_size_bytes'],
                    video_meta['duration_seconds'],
                    video_meta['width'],
                    video_meta['height'],
                    video_meta['fps'],
                    video_meta['codec'],
                    video_meta['audio_tracks'],
                    file_id
                ))

            # Clear old enrichment data
            cur.execute("DELETE FROM scenes WHERE file_id = %s", (file_id,))

            # Re-queue for enrichment (delete old entry if exists, then insert new)
            cur.execute("DELETE FROM enrichment_queue WHERE file_id = %s", (file_id,))
            cur.execute("""
                INSERT INTO enrichment_queue (file_id, status, queued_at)
                VALUES (%s, 'pending', NOW())
            """, (file_id,))

            conn.commit()
            cur.close()
            conn.close()
            return file_id, False, True  # Existing file, was updated

        cur.close()
        conn.close()
        return file_id, False, False

    # New file - add to database
    file_meta = get_file_metadata(filepath)
    filename = os.path.basename(filepath)

    if defer_probe:
        # Insert with minimal metadata - FFprobe runs during enrichment
        logger.debug(f"Adding new file (deferred probe): {filepath}")
        cur.execute(
            """
            INSERT INTO files (
                path, filename,
                file_size_bytes, file_created_at, file_modified_at, parent_folder
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                filepath, filename,
                file_meta['file_size_bytes'], file_meta['file_created_at'],
                file_meta['file_modified_at'], file_meta['parent_folder']
            )
        )
    else:
        # Immediate probe (legacy behavior)
        video_meta = get_video_metadata(filepath)

        # Validate: skip files FFprobe can't read (no duration = unreadable)
        if video_meta['duration_seconds'] is None:
            logger.warning(f"FFprobe failed, skipping: {filepath}")
            cur.close()
            conn.close()
            return None, False, False  # Unreadable file, skip it

        cur.execute(
            """
            INSERT INTO files (
                path, filename,
                duration_seconds, width, height, fps, codec, audio_tracks,
                file_size_bytes, file_created_at, file_modified_at, parent_folder,
                pix_fmt, color_space, color_transfer, color_primaries
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                filepath, filename,
                video_meta['duration_seconds'], video_meta['width'], video_meta['height'],
                video_meta['fps'], video_meta['codec'], video_meta['audio_tracks'],
                file_meta['file_size_bytes'], file_meta['file_created_at'],
                file_meta['file_modified_at'], file_meta['parent_folder'],
                video_meta['pix_fmt'], video_meta['color_space'],
                video_meta['color_transfer'], video_meta['color_primaries']
            )
        )

    file_id = cur.fetchone()[0]

    # Add to enrichment queue
    cur.execute(
        """
        INSERT INTO enrichment_queue (file_id, status, queued_at)
        VALUES (%s, 'pending', NOW())
        """,
        (file_id,)
    )

    conn.commit()
    cur.close()
    conn.close()

    return file_id, True, False  # New file


def recover_stuck_jobs(timeout_minutes=30):
    """
    Reset jobs stuck in 'processing' state for longer than timeout.
    This handles crashes/interruptions during enrichment.
    Returns number of recovered jobs.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE enrichment_queue
        SET status = 'pending', started_at = NULL
        WHERE status = 'processing'
          AND started_at < NOW() - INTERVAL '%s minutes'
        RETURNING id
    """, (timeout_minutes,))
    
    recovered = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    return recovered


def mark_missing_files(watch_folders):
    """
    Mark files as deleted if they no longer exist on disk.
    Only checks files that are currently in the watched folders.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Get all non-deleted files
    cur.execute("""
        SELECT id, path FROM files 
        WHERE deleted_at IS NULL
    """)
    
    deleted_count = 0
    for file_id, path in cur.fetchall():
        # Check if file still exists
        if not os.path.exists(path):
            # Check if this file's parent folder is still being watched
            in_watched = any(path.startswith(folder) for folder in watch_folders)
            if in_watched:
                cur.execute(
                    "UPDATE files SET deleted_at = NOW() WHERE id = %s",
                    (file_id,)
                )
                deleted_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    return deleted_count


def get_stats():
    """
    Get statistics for UI dashboard.
    Returns dict with counts and status info.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    stats = {}
    
    # Total files
    cur.execute("SELECT COUNT(*) FROM files WHERE deleted_at IS NULL")
    stats['total_files'] = cur.fetchone()[0]
    
    # Total scenes
    cur.execute("SELECT COUNT(*) FROM scenes")
    stats['total_scenes'] = cur.fetchone()[0]
    
    # Total faces
    cur.execute("SELECT COUNT(*) FROM faces")
    stats['total_faces'] = cur.fetchone()[0]
    
    # Queue status
    cur.execute("""
        SELECT status, COUNT(*) 
        FROM enrichment_queue 
        GROUP BY status
    """)
    queue_status = dict(cur.fetchall())
    stats['queue_pending'] = queue_status.get('pending', 0)
    stats['queue_processing'] = queue_status.get('processing', 0)
    stats['queue_complete'] = queue_status.get('complete', 0)
    stats['queue_failed'] = queue_status.get('failed', 0)
    
    # Total video duration
    cur.execute("SELECT COALESCE(SUM(duration_seconds), 0) FROM files WHERE deleted_at IS NULL")
    stats['total_duration_seconds'] = cur.fetchone()[0]
    
    # Total storage used by videos
    cur.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM files WHERE deleted_at IS NULL")
    stats['total_file_size_bytes'] = cur.fetchone()[0]
    
    # Last scan info
    stats['last_scan_at'] = get_config('last_scan_at')
    stats['last_scan_duration_ms'] = get_config('last_scan_duration_ms')
    stats['indexer_state'] = get_config('indexer_state', 'running')
    stats['poll_interval_seconds'] = get_config('poll_interval_seconds', 3600)
    
    cur.close()
    conn.close()
    
    return stats


def run_scan():
    """
    Run a full scan of all watch folders.
    Returns (total_found, new_added, updated, skipped).

    Scan is now instant because FFprobe is deferred to enrichment phase.
    Progress is written to DB for UI visibility.
    """
    import time
    start_time = time.time()

    watch_folders = get_watch_folders()

    if not watch_folders:
        print("  No watch folders configured")
        logger.warning("No watch folders configured")
        clear_scan_progress()
        return 0, 0, 0, 0

    total_found = 0
    new_added = 0
    updated = 0
    skipped = 0
    total_dirs_scanned = 0

    # Phase 1: Discover video files (fast - no FFprobe)
    all_videos = []
    for folder in watch_folders:
        print(f"  Discovering videos in: {folder}")
        logger.info(f"Discovering videos in: {folder}")

        def on_progress(dirs_scanned, current_dir):
            update_scan_progress(
                phase='discovering',
                current_folder=current_dir,
                dirs_scanned=total_dirs_scanned + dirs_scanned,
                files_found=total_found + len(all_videos)
            )

        update_scan_progress(
            phase='discovering',
            current_folder=folder,
            dirs_scanned=total_dirs_scanned
        )

        videos = scan_folder(folder, on_progress=on_progress)
        all_videos.extend(videos)
        total_dirs_scanned += 1  # At minimum the root folder

    total_found = len(all_videos)
    logger.info(f"Discovery complete: {total_found} videos found")
    print(f"  Found {total_found} video files")

    # Phase 2: Process files (add to DB - still fast since FFprobe is deferred)
    update_scan_progress(
        phase='processing',
        files_found=total_found,
        files_processed=0
    )

    for i, filepath in enumerate(all_videos):
        file_id, is_new, was_updated = add_file_to_db(filepath, defer_probe=True)

        if file_id is None:
            # File couldn't be accessed (permissions, etc.)
            skipped += 1
            logger.debug(f"Skipped inaccessible file: {filepath}")
            continue

        if is_new:
            new_added += 1
            print(f"    + {os.path.basename(filepath)}")
            logger.info(f"New file: {filepath}")
        elif was_updated:
            updated += 1
            print(f"    ↻ {os.path.basename(filepath)} (modified)")
            logger.info(f"Modified file: {filepath}")

        # Update progress every 10 files or at end
        if (i + 1) % 10 == 0 or i == len(all_videos) - 1:
            update_scan_progress(
                phase='processing',
                files_found=total_found,
                files_processed=i + 1,
                files_new=new_added,
                files_updated=updated,
                files_skipped=skipped
            )

    # Phase 3: Mark missing files
    update_scan_progress(phase='checking_missing')
    logger.info("Checking for missing files...")
    deleted = mark_missing_files(watch_folders)
    if deleted > 0:
        print(f"  Marked {deleted} missing files as deleted")
        logger.info(f"Marked {deleted} missing files as deleted")

    # Log skipped files
    if skipped > 0:
        print(f"  Skipped {skipped} inaccessible files")
        logger.warning(f"Skipped {skipped} inaccessible files")

    # Record scan metadata
    duration_ms = int((time.time() - start_time) * 1000)
    set_config('last_scan_at', datetime.now().isoformat())
    set_config('last_scan_duration_ms', duration_ms)

    # Mark scan complete
    update_scan_progress(
        phase='complete',
        files_found=total_found,
        files_processed=total_found,
        files_new=new_added,
        files_updated=updated,
        files_skipped=skipped
    )

    logger.info(f"Scan complete in {duration_ms}ms: {total_found} found, {new_added} new, {updated} modified")

    return total_found, new_added, updated, skipped
