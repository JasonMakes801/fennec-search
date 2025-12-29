"""
Fennec API Server
FastAPI backend for video search with CLIP, Whisper, and face filtering
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

from db import fetch_one, fetch_all, execute

app = FastAPI(title="Fennec API", version="0.1.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POSTERS_DIR = os.environ.get('POSTERS_DIR', '/app/posters')

# Root paths available for browsing (must match docker-compose mounts)
BROWSE_ROOTS = ['/Users', '/Volumes', '/home', '/mnt', '/media']

# Load CLIP model lazily
_clip_model = None
_clip_tokenizer = None

def get_clip_model():
    """Lazy load CLIP model for text embedding."""
    global _clip_model, _clip_tokenizer
    if _clip_model is None:
        try:
            import open_clip
            _clip_model, _, _ = open_clip.create_model_and_transforms(
                'ViT-B-32', pretrained='laion2b_s34b_b79k'
            )
            _clip_tokenizer = open_clip.get_tokenizer('ViT-B-32')
            _clip_model.eval()
        except Exception as e:
            print(f"Warning: Could not load CLIP model: {e}")
            return None, None
    return _clip_model, _clip_tokenizer

def embed_text(text: str) -> Optional[List[float]]:
    """Embed text using CLIP."""
    import torch
    model, tokenizer = get_clip_model()
    if model is None:
        return None
    
    with torch.no_grad():
        tokens = tokenizer([text])
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
        return embedding[0].cpu().numpy().tolist()


# Load sentence-transformer model lazily (for semantic transcript search)
_sentence_model = None

def get_sentence_model():
    """Lazy load sentence-transformer model for transcript embedding."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Could not load sentence-transformer model: {e}")
            return None
    return _sentence_model

def embed_transcript_text(text: str) -> Optional[List[float]]:
    """Embed text using sentence-transformer for semantic transcript search."""
    model = get_sentence_model()
    if model is None:
        return None
    
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def get_search_thresholds() -> dict:
    """Get search thresholds from config with fallback defaults."""
    defaults = {
        'visual': 0.10,
        'visual_match': 0.20,
        'face': 0.25,
        'transcript': 0.35
    }
    try:
        visual = fetch_one("SELECT value FROM config WHERE key = 'search_threshold_visual'")
        visual_match = fetch_one("SELECT value FROM config WHERE key = 'search_threshold_visual_match'")
        face = fetch_one("SELECT value FROM config WHERE key = 'search_threshold_face'")
        transcript = fetch_one("SELECT value FROM config WHERE key = 'search_threshold_transcript'")
        
        return {
            'visual': float(visual['value']) if visual and visual.get('value') is not None else defaults['visual'],
            'visual_match': float(visual_match['value']) if visual_match and visual_match.get('value') is not None else defaults['visual_match'],
            'face': float(face['value']) if face and face.get('value') is not None else defaults['face'],
            'transcript': float(transcript['value']) if transcript and transcript.get('value') is not None else defaults['transcript']
        }
    except Exception:
        return defaults


# ============ Pydantic Models ============

class ConfigValue(BaseModel):
    value: Any


# ============ Scenes Browse ============

@app.get("/api/scenes")
async def list_scenes(
    limit: int = Query(40, le=200),
    offset: int = Query(0, ge=0)
):
    """Browse scenes with pagination."""
    scenes = fetch_all("""
        SELECT 
            s.id,
            s.scene_index,
            s.start_tc as start_time,
            s.end_tc as end_time,
            s.transcript,
            s.poster_frame_path,
            f.id as file_id,
            f.filename,
            f.path,
            f.duration_seconds,
            f.width,
            f.height,
            f.fps,
            f.codec,
            f.audio_tracks,
            f.file_size_bytes,
            f.file_modified_at
        FROM scenes s
        JOIN files f ON s.file_id = f.id
        WHERE f.deleted_at IS NULL
        ORDER BY s.scene_index
        LIMIT %s OFFSET %s
    """, (limit, offset))
    
    # Get total count
    total = fetch_one("SELECT COUNT(*) as count FROM scenes s JOIN files f ON s.file_id = f.id WHERE f.deleted_at IS NULL")
    
    # Add faces to each scene
    for scene in scenes:
        faces = fetch_all("""
            SELECT id, bbox_x, bbox_y, bbox_w, bbox_h
            FROM faces
            WHERE scene_id = %s
        """, (scene['id'],))
        scene['faces'] = [
            {'id': f['id'], 'bbox': [f['bbox_x'], f['bbox_y'], f['bbox_w'], f['bbox_h']]}
            for f in faces
        ]
    
    return {"scenes": scenes, "total": total['count'] if total else 0}


@app.get("/api/scene/{scene_index}")
async def get_scene(scene_index: int):
    """Get single scene details."""
    scene = fetch_one("""
        SELECT 
            s.id,
            s.scene_index,
            s.start_tc as start_time,
            s.end_tc as end_time,
            s.transcript,
            s.poster_frame_path,
            f.id as file_id,
            f.filename,
            f.path,
            f.duration_seconds,
            f.width,
            f.height,
            f.fps,
            f.codec,
            f.audio_tracks,
            f.file_size_bytes,
            f.file_modified_at
        FROM scenes s
        JOIN files f ON s.file_id = f.id
        WHERE s.scene_index = %s AND f.deleted_at IS NULL
    """, (scene_index,))
    
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    # Get faces
    faces = fetch_all("""
        SELECT id, bbox_x, bbox_y, bbox_w, bbox_h
        FROM faces
        WHERE scene_id = %s
    """, (scene['id'],))
    scene['faces'] = [
        {'id': f['id'], 'bbox': [f['bbox_x'], f['bbox_y'], f['bbox_w'], f['bbox_h']]}
        for f in faces
    ]
    
    # Get embeddings for this scene
    embeddings = fetch_all("""
        SELECT model_name, model_version, dimension
        FROM embeddings
        WHERE scene_id = %s
    """, (scene['id'],))
    scene['vectors'] = [
        {'model': e['model_name'], 'version': e['model_version'], 'dimension': e['dimension']}
        for e in embeddings
    ]
    
    return scene


# ============ Combined Search ============

@app.get("/api/search")
async def search(
    visual: Optional[str] = Query(None, description="Visual search query (CLIP text)"),
    visual_threshold: Optional[float] = Query(None, description="Minimum visual similarity (uses config default if not specified)"),
    transcript: Optional[str] = Query(None, description="Search in transcripts (exact substring match)"),
    transcript_semantic: Optional[str] = Query(None, description="Semantic transcript search (finds synonyms, numbers as words, etc.)"),
    transcript_threshold: Optional[float] = Query(None, description="Minimum transcript semantic similarity (uses config default if not specified)"),
    face_scene: Optional[int] = Query(None, description="Scene index for face filter"),
    face_index: Optional[int] = Query(None, description="Face index within scene"),
    face_id: Optional[int] = Query(None, description="Face ID for direct face filter (from face browser)"),
    face_threshold: Optional[float] = Query(None, description="Minimum face similarity (uses config default if not specified)"),
    visual_match_scene: Optional[int] = Query(None, description="Scene index for visual match"),
    visual_match_threshold: Optional[float] = Query(None, description="Minimum visual match similarity (uses config default if not specified)"),
    tc_min: Optional[float] = Query(None, description="Minimum timecode in seconds"),
    tc_max: Optional[float] = Query(None, description="Maximum timecode in seconds"),
    # Metadata filters
    path: Optional[str] = Query(None, description="Filter by path substring"),
    duration_min: Optional[float] = Query(None, description="Minimum file duration in seconds"),
    duration_max: Optional[float] = Query(None, description="Maximum file duration in seconds"),
    width_min: Optional[int] = Query(None, description="Minimum video width"),
    width_max: Optional[int] = Query(None, description="Maximum video width"),
    height_min: Optional[int] = Query(None, description="Minimum video height"),
    height_max: Optional[int] = Query(None, description="Maximum video height"),
    fps_min: Optional[float] = Query(None, description="Minimum frame rate"),
    fps_max: Optional[float] = Query(None, description="Maximum frame rate"),
    codec: Optional[str] = Query(None, description="Filter by codec (substring match)"),
    limit: int = Query(200, le=500)
):
    """
    Combined search with restrictive/exclusive filters.
    Each filter reduces the result set.
    Threshold defaults come from config if not specified in query.
    """
    
    # Get threshold defaults from config
    config_thresholds = get_search_thresholds()
    if visual_threshold is None:
        visual_threshold = config_thresholds['visual']
    if visual_match_threshold is None:
        visual_match_threshold = config_thresholds['visual_match']
    if face_threshold is None:
        face_threshold = config_thresholds['face']
    if transcript_threshold is None:
        transcript_threshold = config_thresholds['transcript']
    
    # Start with all scenes (join embeddings for CLIP vectors)
    base_query = """
        SELECT 
            s.id,
            s.scene_index,
            s.start_tc as start_time,
            s.end_tc as end_time,
            s.transcript,
            s.poster_frame_path,
            e.embedding as clip_embedding,
            f.id as file_id,
            f.filename,
            f.path,
            f.duration_seconds,
            f.width,
            f.height,
            f.fps,
            f.codec,
            f.audio_tracks,
            f.file_size_bytes,
            f.file_modified_at
        FROM scenes s
        JOIN files f ON s.file_id = f.id
        LEFT JOIN embeddings e ON s.id = e.scene_id AND e.model_name = 'clip'
        WHERE f.deleted_at IS NULL
    """
    params = []
    
    # Timecode filter
    if tc_min is not None:
        base_query += " AND s.start_tc >= %s"
        params.append(tc_min)
    if tc_max is not None:
        base_query += " AND s.end_tc <= %s"
        params.append(tc_max)
    
    # Transcript filter (substring match)
    if transcript:
        base_query += " AND s.transcript ILIKE %s"
        params.append(f'%{transcript}%')
    
    # Path filter (substring match)
    if path:
        base_query += " AND f.path ILIKE %s"
        params.append(f'%{path}%')
    
    # Duration filter
    if duration_min is not None:
        base_query += " AND f.duration_seconds >= %s"
        params.append(duration_min)
    if duration_max is not None:
        base_query += " AND f.duration_seconds <= %s"
        params.append(duration_max)
    
    # Resolution filters
    if width_min is not None:
        base_query += " AND f.width >= %s"
        params.append(width_min)
    if width_max is not None:
        base_query += " AND f.width <= %s"
        params.append(width_max)
    if height_min is not None:
        base_query += " AND f.height >= %s"
        params.append(height_min)
    if height_max is not None:
        base_query += " AND f.height <= %s"
        params.append(height_max)
    
    # FPS filter
    if fps_min is not None:
        base_query += " AND f.fps >= %s"
        params.append(fps_min)
    if fps_max is not None:
        base_query += " AND f.fps <= %s"
        params.append(fps_max)
    
    # Codec filter (substring match)
    if codec:
        base_query += " AND f.codec ILIKE %s"
        params.append(f'%{codec}%')
    
    base_query += " ORDER BY s.scene_index"
    
    # Fetch base results
    scenes = fetch_all(base_query, tuple(params) if params else None)
    
    results = []
    
    # Process visual text search with CLIP
    if visual:
        text_embedding = embed_text(visual)
        if text_embedding:
            text_emb_np = np.array(text_embedding)
            for scene in scenes:
                emb = scene.get('clip_embedding')
                if emb is not None:
                    similarity = float(np.dot(text_emb_np, emb))
                    if similarity >= visual_threshold:
                        scene['similarity'] = similarity
                        results.append(scene)
            # Sort by similarity descending
            results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        else:
            # Fallback: no CLIP model, just use transcript match
            results = scenes
    else:
        results = scenes
    
    # Visual match filter (find scenes similar to reference scene)
    if visual_match_scene is not None:
        ref_scene = fetch_one("""
            SELECT e.embedding as clip_embedding 
            FROM scenes s
            JOIN embeddings e ON s.id = e.scene_id AND e.model_name = 'clip'
            WHERE s.scene_index = %s
        """, (visual_match_scene,))
        
        if ref_scene and ref_scene.get('clip_embedding') is not None:
            ref_emb = ref_scene['clip_embedding']
            filtered = []
            for scene in results:
                emb = scene.get('clip_embedding')
                if emb is not None:
                    similarity = float(np.dot(ref_emb, emb))
                    if similarity >= visual_match_threshold:
                        scene['similarity'] = similarity
                        filtered.append(scene)
            # Sort by similarity descending
            filtered.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            results = filtered
    
    # Face filter - support both face_id (direct) and face_scene+face_index (from clicking results)
    ref_emb = None
    
    if face_id is not None:
        # Direct face lookup by ID
        ref_face = fetch_one("""
            SELECT embedding FROM faces WHERE id = %s
        """, (face_id,))
        if ref_face and ref_face.get('embedding') is not None:
            ref_emb = ref_face['embedding']
    elif face_scene is not None and face_index is not None:
        # Get reference face embedding by scene index and face position
        ref_face = fetch_one("""
            SELECT fa.embedding
            FROM faces fa
            JOIN scenes s ON fa.scene_id = s.id
            WHERE s.scene_index = %s
            ORDER BY fa.id
            LIMIT 1 OFFSET %s
        """, (face_scene, face_index))
        if ref_face and ref_face.get('embedding') is not None:
            ref_emb = ref_face['embedding']
    
    if ref_emb is not None:
        scene_ids = [s['id'] for s in results]
        
        if scene_ids:
            # Find scenes with matching faces
            placeholders = ','.join(['%s'] * len(scene_ids))
            face_matches = fetch_all(f"""
                SELECT DISTINCT scene_id, embedding
                FROM faces
                WHERE scene_id IN ({placeholders})
            """, tuple(scene_ids))
            
            # Calculate face similarities
            scene_face_sims = {}
            for fm in face_matches:
                face_emb = fm.get('embedding')
                if face_emb is not None:
                    similarity = float(np.dot(ref_emb, face_emb))
                    scene_id = fm['scene_id']
                    if scene_id not in scene_face_sims or similarity > scene_face_sims[scene_id]:
                        scene_face_sims[scene_id] = similarity
            
            # Filter by threshold
            filtered = []
            for scene in results:
                face_sim = scene_face_sims.get(scene['id'], 0)
                if face_sim >= face_threshold:
                    scene['face_similarity'] = face_sim
                    filtered.append(scene)
            
            results = filtered
    
    # Semantic transcript search (finds "1" when searching "one", synonyms, etc.)
    if transcript_semantic:
        text_embedding = embed_transcript_text(transcript_semantic)
        if text_embedding:
            text_emb_np = np.array(text_embedding)
            
            # Get transcript embeddings for current results
            scene_ids = [s['id'] for s in results]
            if scene_ids:
                placeholders = ','.join(['%s'] * len(scene_ids))
                transcript_embeddings = fetch_all(f"""
                    SELECT scene_id, embedding
                    FROM embeddings
                    WHERE scene_id IN ({placeholders}) AND model_name = 'sentence-transformer'
                """, tuple(scene_ids))
                
                # Build scene_id -> embedding map
                scene_transcript_embs = {te['scene_id']: te['embedding'] for te in transcript_embeddings}
                
                # Filter by semantic similarity
                filtered = []
                for scene in results:
                    emb = scene_transcript_embs.get(scene['id'])
                    if emb is not None:
                        similarity = float(np.dot(text_emb_np, emb))
                        if similarity >= transcript_threshold:
                            scene['transcript_similarity'] = similarity
                            filtered.append(scene)
                
                # Sort by transcript similarity
                filtered.sort(key=lambda x: x.get('transcript_similarity', 0), reverse=True)
                results = filtered
    
    # Add faces to results
    for scene in results:
        faces = fetch_all("""
            SELECT id, bbox_x, bbox_y, bbox_w, bbox_h
            FROM faces
            WHERE scene_id = %s
        """, (scene['id'],))
        scene['faces'] = [
            {'id': f['id'], 'bbox': [f['bbox_x'], f['bbox_y'], f['bbox_w'], f['bbox_h']]}
            for f in faces
        ]
        # Remove embedding from response
        scene.pop('clip_embedding', None)
    
    return {"results": results[:limit]}


# ============ Thumbnails ============

@app.get("/api/thumbnail/{scene_id}")
async def get_thumbnail(scene_id: str):
    """Serve poster frame (mid-scene) for a scene. Used for results grid."""
    # Handle scene_XXXX format
    if scene_id.startswith('scene_'):
        scene_index = int(scene_id.replace('scene_', ''))
        scene = fetch_one(
            "SELECT poster_frame_path FROM scenes WHERE scene_index = %s",
            (scene_index,)
        )
    else:
        scene = fetch_one(
            "SELECT poster_frame_path FROM scenes WHERE id = %s",
            (int(scene_id),)
        )
    
    if not scene or not scene['poster_frame_path']:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    poster_path = scene['poster_frame_path']
    
    # Handle both absolute and relative paths
    if not os.path.isabs(poster_path):
        poster_path = os.path.join(POSTERS_DIR, poster_path)
    
    if not os.path.exists(poster_path):
        raise HTTPException(status_code=404, detail="Thumbnail file not found")
    
    # Determine media type
    media_type = "image/webp"
    if poster_path.endswith('.jpg') or poster_path.endswith('.jpeg'):
        media_type = "image/jpeg"
    elif poster_path.endswith('.png'):
        media_type = "image/png"
    
    return FileResponse(poster_path, media_type=media_type)


# ============ Video Streaming ============

@app.get("/api/video/{file_id}")
async def serve_video(file_id: int):
    """Serve video file for playback."""
    file = fetch_one("""
        SELECT path FROM files WHERE id = %s AND deleted_at IS NULL
    """, (file_id,))
    
    if not file or not file['path']:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_path = file['path']
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    
    # Determine media type based on extension
    ext = os.path.splitext(video_path)[1].lower()
    media_types = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.mxf': 'application/mxf',
    }
    media_type = media_types.get(ext, 'video/mp4')
    
    return FileResponse(video_path, media_type=media_type)


# ============ Files ============

@app.get("/api/files")
async def list_files(
    limit: int = Query(50, le=500),
    offset: int = 0
):
    """List indexed files (shots)."""
    files = fetch_all("""
        SELECT id, path, filename, duration_seconds, width, height, 
               fps, codec, audio_tracks, file_size_bytes,
               file_created_at, file_modified_at, parent_folder,
               indexed_at, created_at
        FROM files 
        WHERE deleted_at IS NULL
        ORDER BY indexed_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    
    return {"files": files}


@app.get("/api/files/{file_id}")
async def get_file(file_id: int):
    """Get file details with scenes."""
    file = fetch_one("""
        SELECT id, path, filename, duration_seconds, width, height, 
               fps, codec, audio_tracks, file_size_bytes,
               file_created_at, file_modified_at, parent_folder,
               indexed_at, created_at
        FROM files 
        WHERE id = %s AND deleted_at IS NULL
    """, (file_id,))
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    scenes = fetch_all("""
        SELECT id, scene_index, start_tc, end_tc, poster_frame_path, transcript
        FROM scenes
        WHERE file_id = %s
        ORDER BY scene_index
    """, (file_id,))
    
    return {**file, "scenes": scenes}


# ============ Stats ============

@app.get("/api/stats")
async def get_stats():
    """Get index statistics."""
    stats = fetch_one("""
        SELECT 
            (SELECT COUNT(*) FROM files WHERE deleted_at IS NULL) as files,
            (SELECT COALESCE(SUM(duration_seconds), 0) FROM files WHERE deleted_at IS NULL) as total_duration,
            (SELECT COUNT(*) FROM scenes) as scenes,
            (SELECT COUNT(*) FROM faces) as faces,
            (SELECT COUNT(DISTINCT cluster_id) FROM faces WHERE cluster_id IS NOT NULL) as unique_faces,
            (SELECT COUNT(DISTINCT scene_id) FROM faces) as faces_complete
    """)
    
    return stats


@app.get("/api/stats/vectors")
async def get_vector_stats():
    """Get vector embedding statistics by model, with consistent per-scene coverage."""
    total_scenes = fetch_one("SELECT COUNT(*) as count FROM scenes")
    total = total_scenes['count'] if total_scenes else 0
    
    # Count scenes that have completed enrichment (proxy for "scanned")
    # A scene is scanned if its file has indexed_at set
    scanned_scenes = fetch_one("""
        SELECT COUNT(*) as count 
        FROM scenes s 
        JOIN files f ON s.file_id = f.id 
        WHERE f.indexed_at IS NOT NULL
    """)
    scanned = scanned_scenes['count'] if scanned_scenes else 0
    
    # Get embedding stats from embeddings table
    embedding_models = fetch_all("""
        SELECT 
            model_name,
            model_version,
            dimension,
            COUNT(*) as count,
            MAX(created_at) as last_updated
        FROM embeddings
        GROUP BY model_name, model_version, dimension
        ORDER BY model_name
    """)
    
    # Get face stats - count scenes with at least one face (not total faces)
    face_stats = fetch_one("""
        SELECT 
            COUNT(DISTINCT scene_id) as scenes_with_faces,
            COUNT(*) as total_faces
        FROM faces
    """)
    
    # Build unified model list with consistent naming
    models = []
    
    for m in embedding_models:
        # Map internal names to display names and determine if coverage can be partial
        model_info = {
            'clip': {'name': 'Visual', 'partial': False},
            'sentence-transformer': {'name': 'Transcript', 'partial': True}
        }.get(m['model_name'], {'name': m['model_name'], 'partial': False})
        
        models.append({
            "name": model_info['name'],
            "model": m['model_name'],
            "version": m['model_version'],
            "dimension": m['dimension'],
            "scanned": scanned,
            "found": m['count'],
            "coverage": round(m['count'] / total * 100, 1) if total > 0 else 0,
            "partial_expected": model_info['partial'],
            "last_updated": m['last_updated']
        })
    
    # Add faces as a model entry (scene coverage, not face count)
    if face_stats:
        scenes_with_faces = face_stats['scenes_with_faces'] or 0
        models.append({
            "name": "Faces",
            "model": "arcface",
            "version": "buffalo_l",
            "dimension": 512,
            "scanned": scanned,
            "found": scenes_with_faces,
            "coverage": round(scenes_with_faces / total * 100, 1) if total > 0 else 0,
            "partial_expected": True,
            "total_detected": face_stats['total_faces'] or 0,
            "last_updated": None
        })
    
    return {
        "total_scenes": total,
        "models": models
    }


# ============ Faces ============

@app.get("/api/faces")
async def list_faces(limit: int = Query(50, le=200)):
    """List face clusters with counts."""
    faces = fetch_all("""
        SELECT cluster_id, COUNT(*) as count
        FROM faces
        WHERE cluster_id IS NOT NULL
        GROUP BY cluster_id
        ORDER BY count DESC
        LIMIT %s
    """, (limit,))
    
    return {"faces": faces}


@app.get("/api/faces/browse")
async def browse_faces(
    scene_ids: Optional[str] = Query(None, description="Comma-separated scene IDs to filter by")
):
    """
    Get faces grouped by cluster for face browser modal.
    Optionally filter to only faces in specified scenes.
    When filtered, returns one representative face per cluster (most representative).
    """
    # Parse scene_ids if provided
    scene_id_list = None
    if scene_ids:
        scene_id_list = [int(x) for x in scene_ids.split(',') if x.strip()]

    if scene_id_list:
        # Filtered mode: get clusters present in the filtered scenes
        placeholders = ','.join(['%s'] * len(scene_id_list))

        clusters = fetch_all(f"""
            SELECT
                cluster_id,
                COUNT(*) as count
            FROM faces
            WHERE cluster_id IS NOT NULL AND cluster_id >= 0
            AND scene_id IN ({placeholders})
            GROUP BY cluster_id
            ORDER BY count DESC
        """, tuple(scene_id_list))

        unclustered = fetch_one(f"""
            SELECT COUNT(*) as count FROM faces
            WHERE (cluster_id IS NULL OR cluster_id = -1)
            AND scene_id IN ({placeholders})
        """, tuple(scene_id_list))
        unclustered_count = unclustered['count'] if unclustered else 0

        # Get one representative face per cluster (lowest cluster_order)
        faces = fetch_all(f"""
            SELECT DISTINCT ON (COALESCE(f.cluster_id, -1))
                f.id,
                f.scene_id,
                f.cluster_id,
                f.cluster_order,
                f.bbox_x,
                f.bbox_y,
                f.bbox_w,
                f.bbox_h,
                s.scene_index,
                s.poster_frame_path
            FROM faces f
            JOIN scenes s ON f.scene_id = s.id
            WHERE f.scene_id IN ({placeholders})
            ORDER BY COALESCE(f.cluster_id, -1), f.cluster_order
        """, tuple(scene_id_list))
    else:
        # Unfiltered mode: return all faces
        clusters = fetch_all("""
            SELECT
                cluster_id,
                COUNT(*) as count
            FROM faces
            WHERE cluster_id IS NOT NULL AND cluster_id >= 0
            GROUP BY cluster_id
            ORDER BY count DESC
        """)

        unclustered = fetch_one("""
            SELECT COUNT(*) as count FROM faces WHERE cluster_id IS NULL OR cluster_id = -1
        """)
        unclustered_count = unclustered['count'] if unclustered else 0

        faces = fetch_all("""
            SELECT
                f.id,
                f.scene_id,
                f.cluster_id,
                f.cluster_order,
                f.bbox_x,
                f.bbox_y,
                f.bbox_w,
                f.bbox_h,
                s.scene_index,
                s.poster_frame_path
            FROM faces f
            JOIN scenes s ON f.scene_id = s.id
            ORDER BY
                CASE WHEN f.cluster_id IS NULL OR f.cluster_id = -1 THEN 1 ELSE 0 END,
                f.cluster_id,
                f.cluster_order
        """)

    return {
        "clusters": [
            {"id": c['cluster_id'], "count": c['count']}
            for c in clusters
        ],
        "unclustered_count": unclustered_count,
        "faces": [
            {
                "id": f['id'],
                "scene_id": f['scene_id'],
                "scene_index": f['scene_index'],
                "cluster_id": f['cluster_id'],
                "bbox": [f['bbox_x'], f['bbox_y'], f['bbox_w'], f['bbox_h']],
                "poster_path": f['poster_frame_path']
            }
            for f in faces
        ],
        "filtered": scene_id_list is not None
    }


@app.get("/api/scenes/browse")
async def browse_scenes(
    scene_ids: Optional[str] = Query(None, description="Comma-separated scene IDs to filter by")
):
    """
    Get scenes grouped by CLIP cluster for visual match browser.
    Optionally filter to specified scenes.
    Returns one representative scene per cluster (most representative).
    """
    # Parse scene_ids if provided
    scene_id_list = None
    if scene_ids:
        scene_id_list = [int(x) for x in scene_ids.split(',') if x.strip()]

    if scene_id_list:
        # Filtered mode: get clusters present in the filtered scenes
        placeholders = ','.join(['%s'] * len(scene_id_list))

        clusters = fetch_all(f"""
            SELECT
                clip_cluster_id as cluster_id,
                COUNT(*) as count
            FROM scenes s
            JOIN files f ON s.file_id = f.id
            WHERE clip_cluster_id IS NOT NULL AND clip_cluster_id >= 0
            AND f.deleted_at IS NULL
            AND s.id IN ({placeholders})
            GROUP BY clip_cluster_id
            ORDER BY count DESC
        """, tuple(scene_id_list))

        unclustered = fetch_one(f"""
            SELECT COUNT(*) as count FROM scenes s
            JOIN files f ON s.file_id = f.id
            WHERE (clip_cluster_id IS NULL OR clip_cluster_id = -1)
            AND f.deleted_at IS NULL
            AND s.id IN ({placeholders})
        """, tuple(scene_id_list))
        unclustered_count = unclustered['count'] if unclustered else 0

        # Get one representative scene per cluster (lowest clip_cluster_order)
        scenes = fetch_all(f"""
            SELECT DISTINCT ON (COALESCE(s.clip_cluster_id, -1))
                s.id,
                s.scene_index,
                s.clip_cluster_id as cluster_id,
                s.clip_cluster_order,
                s.start_tc,
                s.end_tc,
                s.poster_frame_path,
                f.id as file_id,
                f.filename
            FROM scenes s
            JOIN files f ON s.file_id = f.id
            WHERE f.deleted_at IS NULL
            AND s.id IN ({placeholders})
            ORDER BY COALESCE(s.clip_cluster_id, -1), s.clip_cluster_order
        """, tuple(scene_id_list))
    else:
        # Unfiltered mode: return all scenes (one per cluster)
        clusters = fetch_all("""
            SELECT
                clip_cluster_id as cluster_id,
                COUNT(*) as count
            FROM scenes s
            JOIN files f ON s.file_id = f.id
            WHERE clip_cluster_id IS NOT NULL AND clip_cluster_id >= 0
            AND f.deleted_at IS NULL
            GROUP BY clip_cluster_id
            ORDER BY count DESC
        """)

        unclustered = fetch_one("""
            SELECT COUNT(*) as count FROM scenes s
            JOIN files f ON s.file_id = f.id
            WHERE (clip_cluster_id IS NULL OR clip_cluster_id = -1)
            AND f.deleted_at IS NULL
        """)
        unclustered_count = unclustered['count'] if unclustered else 0

        # Get one representative scene per cluster
        scenes = fetch_all("""
            SELECT DISTINCT ON (COALESCE(s.clip_cluster_id, -1))
                s.id,
                s.scene_index,
                s.clip_cluster_id as cluster_id,
                s.clip_cluster_order,
                s.start_tc,
                s.end_tc,
                s.poster_frame_path,
                f.id as file_id,
                f.filename
            FROM scenes s
            JOIN files f ON s.file_id = f.id
            WHERE f.deleted_at IS NULL
            ORDER BY COALESCE(s.clip_cluster_id, -1), s.clip_cluster_order
        """)

    return {
        "clusters": [
            {"id": c['cluster_id'], "count": c['count']}
            for c in clusters
        ],
        "unclustered_count": unclustered_count,
        "scenes": [
            {
                "id": s['id'],
                "scene_index": s['scene_index'],
                "cluster_id": s['cluster_id'],
                "start_time": s['start_tc'],
                "end_time": s['end_tc'],
                "poster_path": s['poster_frame_path'],
                "file_id": s['file_id'],
                "filename": s['filename']
            }
            for s in scenes
        ],
        "filtered": scene_id_list is not None
    }


@app.get("/api/faces/{face_id}")
async def get_face(face_id: int):
    """Get a single face with its scene and file info."""
    face = fetch_one("""
        SELECT 
            f.id,
            f.scene_id,
            f.cluster_id,
            f.bbox_x,
            f.bbox_y,
            f.bbox_w,
            f.bbox_h,
            s.scene_index,
            s.poster_frame_path,
            s.start_tc,
            s.end_tc,
            fi.id as file_id,
            fi.filename,
            fi.path
        FROM faces f
        JOIN scenes s ON f.scene_id = s.id
        JOIN files fi ON s.file_id = fi.id
        WHERE f.id = %s
    """, (face_id,))
    
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")
    
    return {
        "id": face['id'],
        "scene_id": face['scene_id'],
        "scene_index": face['scene_index'],
        "cluster_id": face['cluster_id'],
        "bbox": [face['bbox_x'], face['bbox_y'], face['bbox_w'], face['bbox_h']],
        "poster_path": face['poster_frame_path'],
        "start_tc": face['start_tc'],
        "end_tc": face['end_tc'],
        "file_id": face['file_id'],
        "filename": face['filename'],
        "path": face['path']
    }


# ============ Queue ============

@app.get("/api/queue")
async def get_queue():
    """Get enrichment queue status including current processing job."""
    stats = fetch_one("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'processing') as processing,
            COUNT(*) FILTER (WHERE status = 'complete') as complete,
            COUNT(*) FILTER (WHERE status = 'failed') as failed
        FROM enrichment_queue
    """)
    
    # Get currently processing job details
    current = fetch_one("""
        SELECT 
            eq.id,
            eq.current_stage,
            eq.current_stage_num,
            eq.total_stages,
            eq.started_at,
            f.filename,
            f.path,
            f.duration_seconds
        FROM enrichment_queue eq
        JOIN files f ON f.id = eq.file_id
        WHERE eq.status = 'processing'
        ORDER BY eq.started_at DESC
        LIMIT 1
    """)
    
    return {
        **stats,
        'current': current
    }


# ============ Config ============

@app.get("/api/config/{key}")
async def get_config(key: str):
    """Get a single configuration value."""
    row = fetch_one("SELECT value FROM config WHERE key = %s", (key,))
    if not row:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    return {"value": row['value']}


@app.put("/api/config/{key}")
async def set_config(key: str, body: ConfigValue):
    """Set a configuration value."""
    existing = fetch_one("SELECT key FROM config WHERE key = %s", (key,))
    
    if existing:
        execute(
            "UPDATE config SET value = %s WHERE key = %s",
            (json.dumps(body.value), key)
        )
    else:
        execute(
            "INSERT INTO config (key, value) VALUES (%s, %s)",
            (key, json.dumps(body.value))
        )
    
    return {"success": True, "key": key, "value": body.value}


# ============ Health ============

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    try:
        fetch_one("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)}
        )
