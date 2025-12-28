"""
Fennec Ingest Service - Entry point
Polls folders for video files and queues them for enrichment.
Uses simple polling (not watchdog) for NFS/SMB compatibility.
"""

import os
import time
from db import get_connection
from scanner import run_scan, get_stats, get_indexer_state, get_poll_interval, recover_stuck_jobs, set_config, get_config
from enrichment import run_enrichment
from face_cluster import cluster_faces


def format_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_bytes(size_bytes):
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def print_stats():
    """Print current indexer statistics."""
    stats = get_stats()
    print(f"\n📊 Index stats:")
    print(f"   Files: {stats['total_files']}")
    print(f"   Scenes: {stats['total_scenes']}")
    print(f"   Faces: {stats['total_faces']}")
    print(f"   Video duration: {format_duration(stats['total_duration_seconds'])}")
    print(f"   Video storage: {format_bytes(stats['total_file_size_bytes'])}")
    
    pending = stats['queue_pending']
    if pending > 0:
        print(f"   Queue: {pending} pending")
    if stats['queue_failed'] > 0:
        print(f"   ⚠️  Failed jobs: {stats['queue_failed']}")


def sync_watch_folders_from_env():
    """Sync WATCH_FOLDERS env var to config table on startup."""
    env_folders = os.environ.get('WATCH_FOLDERS', '')
    if not env_folders.strip():
        return
    
    # Parse comma-separated paths
    folders = [f.strip() for f in env_folders.split(',') if f.strip()]
    if folders:
        set_config('watch_folders', folders)
        print(f"✓ Watch folders from env: {', '.join(folders)}")


def main():
    print("🦊 Fennec Ingest Service starting...")
    
    # Test database connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM files WHERE deleted_at IS NULL")
    count = cur.fetchone()[0]
    print(f"✓ Database connected. Files in index: {count}")
    cur.close()
    conn.close()
    
    # Sync watch folders from environment variable
    sync_watch_folders_from_env()
    
    # Recover any stuck jobs from previous runs
    recovered = recover_stuck_jobs(timeout_minutes=30)
    if recovered > 0:
        print(f"↻ Recovered {recovered} stuck job(s) from previous run")
    
    # Main polling loop
    while True:
        state = get_indexer_state()
        
        if state == 'paused':
            print("⏸️  Indexer paused. Waiting...")
            time.sleep(30)
            continue
        
        # Run scan
        print("\n🔍 Scanning watch folders...")
        total, new, updated, skipped = run_scan()
        status_parts = [f"Found {total} videos"]
        if new > 0:
            status_parts.append(f"{new} new")
        if updated > 0:
            status_parts.append(f"{updated} modified")
        if skipped > 0:
            status_parts.append(f"{skipped} skipped")
        print(f"✓ Scan complete. {', '.join(status_parts)}.")
        
        # Get pending count
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM enrichment_queue WHERE status = 'pending'")
        pending = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        # Process pending enrichment jobs
        if pending > 0:
            print(f"\n⚙️  Processing {pending} pending files...")
            processed = run_enrichment()
            print(f"✓ Enrichment complete. Processed {processed} files.")
            
            # Re-cluster all faces after new files processed
            print(f"\n🧩 Clustering faces...")
            cluster_faces()
        
        # Print stats
        print_stats()
        
        # Wait for next poll
        poll_interval = get_poll_interval()
        print(f"\n💤 Next scan in {format_duration(poll_interval)}... (Ctrl+C to stop)")
        
        # Sleep in small increments so we can respond to state changes
        sleep_start = time.time()
        while time.time() - sleep_start < poll_interval:
            # Check if state changed (e.g. paused -> running)
            new_state = get_indexer_state()
            if new_state != state:
                print(f"   State changed to: {new_state}")
                break
            time.sleep(10)


if __name__ == "__main__":
    main()
