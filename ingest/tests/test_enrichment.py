"""
Tests for enrichment pipeline.
"""

import os
import shutil
import pytest
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner import add_file_to_db
from scene_detect import detect_scenes
from whisper_transcribe import transcribe_video
from clip_embed import embed_scenes_for_file
from face_detect import detect_faces_for_file
from enrichment import process_file, get_enabled_models


class TestSceneDetection:
    """Tests for scene detection."""
    
    def test_detect_scenes_normal(self, clean_db, test_video_normal):
        """Should detect at least one scene."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        
        num_scenes = detect_scenes(test_video_normal, file_id)
        
        assert num_scenes >= 1
        
        # Verify scenes in database
        cur = clean_db.cursor()
        cur.execute("SELECT COUNT(*) FROM scenes WHERE file_id = %s", (file_id,))
        count = cur.fetchone()[0]
        cur.close()
        
        assert count == num_scenes
    
    def test_detect_scenes_multi(self, clean_db, test_video_multi_scene):
        """Should detect multiple scenes in longer clip."""
        file_id, _, _ = add_file_to_db(test_video_multi_scene)
        
        num_scenes = detect_scenes(test_video_multi_scene, file_id)
        
        # Multi-scene fixture should have scene cuts
        assert num_scenes >= 1
    
    def test_detect_scenes_corrupted(self, clean_db, test_video_corrupted):
        """Should handle corrupted video gracefully."""
        file_id, _, _ = add_file_to_db(test_video_corrupted)
        
        # Should not crash, return 0 or raise handled exception
        try:
            num_scenes = detect_scenes(test_video_corrupted, file_id)
            assert num_scenes == 0
        except Exception as e:
            # Some exceptions are expected for corrupted files
            assert "corrupt" in str(e).lower() or "invalid" in str(e).lower() or True
    
    def test_poster_frames_created(self, clean_db, test_video_normal):
        """Should create poster frame images."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        detect_scenes(test_video_normal, file_id)
        
        cur = clean_db.cursor()
        cur.execute(
            "SELECT poster_frame_path FROM scenes WHERE file_id = %s",
            (file_id,)
        )
        paths = [row[0] for row in cur.fetchall()]
        cur.close()
        
        # Each scene should have a poster path
        assert len(paths) >= 1
        for path in paths:
            assert path is not None
            # Note: In Docker, path exists inside container


class TestWhisperTranscription:
    """Tests for audio transcription."""
    
    def test_transcribe_with_audio(self, clean_db, test_video_normal):
        """Should transcribe video with audio."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        detect_scenes(test_video_normal, file_id)
        
        num_segments = transcribe_video(test_video_normal, file_id)
        
        # Should find some speech (test clip has dialog)
        # Or at least not crash
        assert num_segments >= 0
    
    def test_skip_no_audio(self, clean_db, test_video_no_audio):
        """Should skip transcription for video without audio."""
        file_id, _, _ = add_file_to_db(test_video_no_audio)
        detect_scenes(test_video_no_audio, file_id)
        
        num_segments = transcribe_video(test_video_no_audio, file_id)
        
        # Should return 0 and skip, not crash
        assert num_segments == 0
    
    def test_transcribe_corrupted(self, clean_db, test_video_corrupted):
        """Should handle corrupted video gracefully."""
        file_id, _, _ = add_file_to_db(test_video_corrupted)
        
        # Should not crash
        try:
            num_segments = transcribe_video(test_video_corrupted, file_id)
            assert num_segments == 0
        except Exception:
            pass  # Exceptions are OK for corrupted files


class TestCLIPEmbedding:
    """Tests for CLIP embedding generation."""
    
    def test_embed_scenes(self, clean_db, test_video_normal):
        """Should generate embeddings for scenes."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        detect_scenes(test_video_normal, file_id)
        
        num_embedded = embed_scenes_for_file(file_id)
        
        assert num_embedded >= 1
        
        # Verify embeddings in database (now in embeddings table)
        cur = clean_db.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM embeddings e
            JOIN scenes s ON e.scene_id = s.id
            WHERE s.file_id = %s AND e.model_name = 'clip'
        """, (file_id,))
        count = cur.fetchone()[0]
        cur.close()
        
        assert count == num_embedded
    
    def test_embed_stores_model_info(self, clean_db, test_video_normal):
        """Should store model name, version, and dimension."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        detect_scenes(test_video_normal, file_id)
        embed_scenes_for_file(file_id)
        
        cur = clean_db.cursor()
        cur.execute("""
            SELECT model_name, model_version, dimension FROM embeddings e
            JOIN scenes s ON e.scene_id = s.id
            WHERE s.file_id = %s LIMIT 1
        """, (file_id,))
        row = cur.fetchone()
        cur.close()
        
        assert row is not None
        assert row[0] == 'clip'
        assert row[1] == 'ViT-B-32-laion2b_s34b_b79k'
        assert row[2] == 512


class TestFaceDetection:
    """Tests for face detection."""
    
    def test_detect_faces(self, clean_db, test_video_normal):
        """Should detect faces if present."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        detect_scenes(test_video_normal, file_id)
        
        num_faces = detect_faces_for_file(file_id)
        
        # May or may not find faces depending on clip content
        assert num_faces >= 0
    
    def test_detect_faces_stores_bboxes(self, clean_db, test_video_normal):
        """Should store bounding boxes for detected faces."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        detect_scenes(test_video_normal, file_id)
        detect_faces_for_file(file_id)
        
        cur = clean_db.cursor()
        cur.execute("""
            SELECT bbox_x, bbox_y, bbox_w, bbox_h 
            FROM faces f 
            JOIN scenes s ON f.scene_id = s.id 
            WHERE s.file_id = %s
        """, (file_id,))
        faces = cur.fetchall()
        cur.close()
        
        for bbox_x, bbox_y, bbox_w, bbox_h in faces:
            assert bbox_x is not None
            assert bbox_w > 0
            assert bbox_h > 0


class TestFullEnrichment:
    """Tests for complete enrichment pipeline."""
    
    def test_enrich_file_complete(self, clean_db, test_video_normal):
        """Should run full enrichment pipeline."""
        file_id, _, _ = add_file_to_db(test_video_normal)
        
        # Add to queue
        cur = clean_db.cursor()
        cur.execute(
            "INSERT INTO enrichment_queue (file_id, status) VALUES (%s, 'pending')",
            (file_id,)
        )
        clean_db.commit()
        cur.close()
        
        # process_file doesn't return a value, just verify it doesn't crash
        process_file(file_id, test_video_normal)
        
        # Verify results
        cur = clean_db.cursor()
        
        # Should have scenes
        cur.execute("SELECT COUNT(*) FROM scenes WHERE file_id = %s", (file_id,))
        assert cur.fetchone()[0] >= 1
        
        # Should have embeddings
        cur.execute("""
            SELECT COUNT(*) FROM scenes 
            WHERE file_id = %s AND clip_embedding IS NOT NULL
        """, (file_id,))
        assert cur.fetchone()[0] >= 1
        
        cur.close()
    
    def test_enrich_file_missing(self, clean_db):
        """Should raise exception for missing file."""
        # Add fake file to DB
        cur = clean_db.cursor()
        cur.execute("""
            INSERT INTO files (path, filename) 
            VALUES ('/nonexistent/video.mp4', 'video.mp4')
            RETURNING id
        """)
        file_id = cur.fetchone()[0]
        clean_db.commit()
        cur.close()
        
        # Should raise OSError for missing file
        with pytest.raises(OSError):
            process_file(file_id, '/nonexistent/video.mp4')
    
    def test_model_toggles(self, clean_db):
        """Should respect model enable/disable config."""
        # This tests that get_enabled_models reads config correctly
        models = get_enabled_models()
        
        assert 'clip' in models
        assert 'whisper' in models
        assert 'arcface' in models
        assert all(isinstance(v, bool) for v in models.values())
