"""
ArcFace face detection and embedding.
Uses InsightFace with buffalo_l model for CPU inference.
"""

import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from db import get_connection
from progress import progress_counter, progress_done

# Global model (loaded once)
_app = None


def load_model():
    """Load InsightFace model (buffalo_l). Downloads on first run (~300MB)."""
    global _app
    
    if _app is not None:
        return _app
    
    print("    Loading ArcFace model (first run downloads ~300MB)...")
    
    _app = FaceAnalysis(
        name='buffalo_l',
        providers=['CPUExecutionProvider']
    )
    _app.prepare(ctx_id=-1, det_size=(640, 640))
    
    print("    ✓ ArcFace model loaded")
    return _app


def detect_faces_in_image(image_path):
    """
    Detect faces in an image.
    Returns list of (embedding, bbox) tuples.
    """
    app = load_model()
    
    img = cv2.imread(image_path)
    if img is None:
        return []
    
    faces = app.get(img)
    
    results = []
    for face in faces:
        if face.embedding is not None:
            # Normalize embedding
            embedding = face.embedding / np.linalg.norm(face.embedding)
            
            # Get bounding box (x, y, w, h)
            bbox = face.bbox  # [x1, y1, x2, y2]
            x = float(bbox[0])
            y = float(bbox[1])
            w = float(bbox[2] - bbox[0])
            h = float(bbox[3] - bbox[1])
            
            results.append((embedding, x, y, w, h))
    
    return results


def detect_faces_for_file(file_id):
    """
    Detect faces in all scenes of a file.
    Returns number of faces detected.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Get scenes with poster frames
    cur.execute("""
        SELECT id, poster_frame_path 
        FROM scenes 
        WHERE file_id = %s 
        AND poster_frame_path IS NOT NULL
    """, (file_id,))
    
    scenes = cur.fetchall()
    
    if not scenes:
        cur.close()
        conn.close()
        return 0
    
    # Clear existing faces for this file's scenes
    cur.execute("""
        DELETE FROM faces 
        WHERE scene_id IN (SELECT id FROM scenes WHERE file_id = %s)
    """, (file_id,))
    
    total_faces = 0
    total_scenes = len(scenes)
    
    for i, (scene_id, poster_path) in enumerate(scenes, 1):
        progress_counter(i, total_scenes, f"Detecting faces ({total_faces} found)")
        try:
            faces = detect_faces_in_image(poster_path)
            
            for embedding, x, y, w, h in faces:
                embedding_list = embedding.tolist()
                cur.execute(
                    """
                    INSERT INTO faces (scene_id, embedding, bbox_x, bbox_y, bbox_w, bbox_h)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (scene_id, embedding_list, x, y, w, h)
                )
                total_faces += 1
                
        except Exception as e:
            pass  # Skip frames with detection errors
    
    conn.commit()
    cur.close()
    conn.close()
    
    progress_done(f"{total_faces} faces detected")
    return total_faces
