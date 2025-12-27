"""
Tests for file scanner functionality.
"""

import os
import shutil
import pytest
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner import (
    get_video_extensions,
    get_video_metadata,
    get_file_metadata,
    is_video_file,
    scan_folder,
    add_file_to_db,
    mark_missing_files,
    get_stats,
)


class TestVideoExtensions:
    """Tests for video format detection."""
    
    def test_get_video_extensions_returns_set(self):
        """Should return a set of extensions."""
        exts = get_video_extensions()
        assert isinstance(exts, set)
        assert len(exts) > 0
    
    def test_common_formats_included(self):
        """Should include common video formats."""
        exts = get_video_extensions()
        assert '.mp4' in exts
        assert '.mov' in exts
        assert '.mkv' in exts
    
    def test_is_video_file_positive(self, test_video_normal):
        """Should identify video files."""
        assert is_video_file(test_video_normal) is True
    
    def test_is_video_file_negative(self):
        """Should reject non-video files."""
        assert is_video_file("/path/to/file.txt") is False
        assert is_video_file("/path/to/image.jpg") is False
        assert is_video_file("/path/to/audio.mp3") is False


class TestMetadataExtraction:
    """Tests for FFprobe metadata extraction."""
    
    def test_video_metadata_normal(self, test_video_normal):
        """Should extract metadata from normal video."""
        meta = get_video_metadata(test_video_normal)
        
        assert meta['duration_seconds'] is not None
        assert meta['duration_seconds'] > 0
        assert meta['width'] == 640  # Our test fixture is 640p
        assert meta['height'] is not None
        assert meta['fps'] is not None
        assert meta['codec'] is not None
        assert meta['audio_tracks'] == 1  # Has audio
    
    def test_video_metadata_no_audio(self, test_video_no_audio):
        """Should detect video has no audio tracks."""
        meta = get_video_metadata(test_video_no_audio)
        
        assert meta['audio_tracks'] == 0
        assert meta['duration_seconds'] > 0
    
    def test_video_metadata_corrupted(self, test_video_corrupted):
        """Should handle corrupted files gracefully."""
        meta = get_video_metadata(test_video_corrupted)
        
        # Should return defaults, not crash
        assert meta is not None
        # Most fields will be None for corrupted files
    
    def test_file_metadata(self, test_video_normal):
        """Should extract file system metadata."""
        meta = get_file_metadata(test_video_normal)
        
        assert meta['file_size_bytes'] > 0
        assert meta['file_created_at'] is not None
        assert meta['file_modified_at'] is not None
        assert meta['parent_folder'] == 'fixtures'


class TestFileScanning:
    """Tests for folder scanning."""
    
    def test_scan_folder_finds_videos(self, temp_watch_folder, test_video_normal):
        """Should find video files in watch folder."""
        # Copy test video to watch folder
        dest = os.path.join(temp_watch_folder, "video.mp4")
        shutil.copy(test_video_normal, dest)
        
        files = list(scan_folder(temp_watch_folder))
        assert len(files) == 1
        assert files[0] == dest
    
    def test_scan_folder_ignores_non_video(self, temp_watch_folder):
        """Should ignore non-video files."""
        # Create non-video file
        txt_file = os.path.join(temp_watch_folder, "readme.txt")
        with open(txt_file, 'w') as f:
            f.write("test")
        
        files = list(scan_folder(temp_watch_folder))
        assert len(files) == 0
    
    def test_scan_folder_recursive(self, temp_watch_folder, test_video_normal):
        """Should scan subdirectories."""
        # Create subdirectory with video
        subdir = os.path.join(temp_watch_folder, "subdir")
        os.makedirs(subdir)
        dest = os.path.join(subdir, "video.mp4")
        shutil.copy(test_video_normal, dest)
        
        files = list(scan_folder(temp_watch_folder))
        assert len(files) == 1
        assert "subdir" in files[0]
    
    def test_scan_missing_folder(self):
        """Should handle missing folders gracefully."""
        files = list(scan_folder("/nonexistent/path"))
        assert len(files) == 0


class TestDatabaseOperations:
    """Tests for database file operations."""
    
    def test_add_file_to_db(self, clean_db, test_video_normal):
        """Should add new file to database."""
        file_id, is_new = add_file_to_db(test_video_normal)
        
        assert file_id is not None
        assert file_id > 0
        assert is_new is True
        
        # Verify in database
        cur = clean_db.cursor()
        cur.execute("SELECT path, filename FROM files WHERE id = %s", (file_id,))
        row = cur.fetchone()
        cur.close()
        
        assert row is not None
        assert row[0] == test_video_normal
        assert row[1] == "test_normal.mp4"
    
    def test_add_file_duplicate(self, clean_db, test_video_normal):
        """Should not duplicate files on re-scan."""
        file_id1, is_new1 = add_file_to_db(test_video_normal)
        file_id2, is_new2 = add_file_to_db(test_video_normal)
        
        # Should return same ID, marked as not new
        assert file_id2 == file_id1
        assert is_new1 is True
        assert is_new2 is False
        
        # Should only have one file in DB
        cur = clean_db.cursor()
        cur.execute("SELECT COUNT(*) FROM files WHERE path = %s", (test_video_normal,))
        count = cur.fetchone()[0]
        cur.close()
        
        assert count == 1
    
    def test_mark_missing_files(self, clean_db, test_video_normal, temp_watch_folder):
        """Should soft-delete files that no longer exist."""
        # Copy test video to watch folder
        dest = os.path.join(temp_watch_folder, "video.mp4")
        shutil.copy(test_video_normal, dest)
        file_id, _ = add_file_to_db(dest)
        
        # Verify it's not deleted
        cur = clean_db.cursor()
        cur.execute("SELECT deleted_at FROM files WHERE id = %s", (file_id,))
        assert cur.fetchone()[0] is None
        
        # Delete the actual file
        os.remove(dest)
        
        # Run mark_missing_files with watch folders
        mark_missing_files([temp_watch_folder])
        
        # Should now be soft-deleted
        cur.execute("SELECT deleted_at FROM files WHERE id = %s", (file_id,))
        assert cur.fetchone()[0] is not None
        cur.close()


class TestStats:
    """Tests for statistics gathering."""
    
    def test_get_stats_empty(self, clean_db):
        """Should return zeros for empty database."""
        stats = get_stats()
        
        assert stats['total_files'] == 0
        assert stats['total_scenes'] == 0
        assert stats['total_faces'] == 0
        assert stats['total_duration_seconds'] == 0
    
    def test_get_stats_with_data(self, clean_db, test_video_normal):
        """Should count files correctly."""
        file_id, _ = add_file_to_db(test_video_normal)
        
        stats = get_stats()
        assert stats['total_files'] == 1
        assert stats['total_duration_seconds'] > 0
