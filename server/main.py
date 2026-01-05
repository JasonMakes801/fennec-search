"""
Fennec API Server
FastAPI backend for video search with CLIP, Whisper, and face filtering
"""

import os
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Any
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

from db import fetch_one, fetch_all, execute


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Load models synchronously at startup (avoids thread pool issues with PyTorch)
    print("Loading models...")
    get_clip_model()
    get_sentence_model()
    print("✓ Models preloaded and ready")
    yield


app = FastAPI(title="Fennec API", version="0.1.0", lifespan=lifespan)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_visits(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in ("/api/search", "/api/scenes", "/"):
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.client.host
        print(f"👀 VISIT: {ip} - {request.url.path}")
    return response


POSTERS_DIR = os.environ.get('POSTERS_DIR', '/app/posters')

# Model status tracking (set to True when loaded)
_clip_loaded = False
_sentence_loaded = False

# Load CLIP model lazily
_clip_model = None
_clip_tokenizer = None

def get_clip_model():
    """Lazy load CLIP model for text embedding."""
    global _clip_model, _clip_tokenizer, _clip_loaded
    if _clip_model is None:
        try:
            import open_clip
            _clip_model, _, _ = open_clip.create_model_and_transforms(
                'ViT-B-32', pretrained='laion2b_s34b_b79k'
            )
            _clip_tokenizer = open_clip.get_tokenizer('ViT-B-32')
            _clip_model.eval()
            _clip_loaded = True
            print("✓ CLIP model loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load CLIP model: {e}")
            import traceback
            traceback.print_exc()
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
    global _sentence_model, _sentence_loaded
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            _sentence_loaded = True
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


class EDLSceneItem(BaseModel):
    sceneId: int
    inTc: float  # seconds
    outTc: float  # seconds


class EDLExportRequest(BaseModel):
    scenes: List[EDLSceneItem]
    title: Optional[str] = "Fennec Export"


# ============ Status ============

@app.get("/api/ready")
async def get_ready_status():
    """Check server readiness - models and indexer state."""
    indexer_row = fetch_one("SELECT value FROM config WHERE key = 'indexer_state'")
    indexer_state = indexer_row['value'] if indexer_row else 'offline'

    return {
        "models_ready": _clip_loaded and _sentence_loaded,
        "clip_loaded": _clip_loaded,
        "sentence_loaded": _sentence_loaded,
        "indexer_state": indexer_state,
    }


# ============ Scenes Browse ============

@app.get("/api/scenes")
async def list_scenes(
    limit: int = Query(40, le=200),
    offset: int = Query(0, ge=0)
):
    """Browse scenes with pagination. Only shows scenes from completed files."""
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
        AND EXISTS (
            SELECT 1 FROM enrichment_queue eq
            WHERE eq.file_id = f.id AND eq.status = 'complete'
        )
        ORDER BY f.filename, s.scene_index
        LIMIT %s OFFSET %s
    """, (limit, offset))

    # Get total count (only completed files)
    total = fetch_one("""
        SELECT COUNT(*) as count FROM scenes s
        JOIN files f ON s.file_id = f.id
        WHERE f.deleted_at IS NULL
        AND EXISTS (
            SELECT 1 FROM enrichment_queue eq
            WHERE eq.file_id = f.id AND eq.status = 'complete'
        )
    """)
    
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
    
    # Get faces for overlay display
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

    # Add ArcFace info if faces exist (stored in faces table, not embeddings)
    if faces:
        scene['vectors'].append({
            'model': 'arcface',
            'version': 'buffalo_l',
            'dimension': 512,
            'count': len(faces)
        })

    return scene


# ============ Combined Search ============

@app.get("/api/search")
async def search(
    visual: Optional[str] = Query(None, description="Visual search query (CLIP text)"),
    visual_threshold: Optional[float] = Query(None, description="Minimum visual similarity (uses config default if not specified)"),
    transcript: Optional[str] = Query(None, description="Search in transcripts (exact substring match)"),
    transcript_semantic: Optional[str] = Query(None, description="Semantic transcript search (finds synonyms, numbers as words, etc.)"),
    transcript_threshold: Optional[float] = Query(None, description="Minimum transcript semantic similarity (uses config default if not specified)"),
    face_id: Optional[int] = Query(None, description="Face ID for face filter"),
    face_threshold: Optional[float] = Query(None, description="Minimum face similarity (uses config default if not specified)"),
    visual_match_scene_id: Optional[int] = Query(None, description="Scene ID for visual match"),
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
    # Only show scenes from files that have completed enrichment
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
        AND EXISTS (
            SELECT 1 FROM enrichment_queue eq
            WHERE eq.file_id = f.id AND eq.status = 'complete'
        )
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
    
    base_query += " ORDER BY f.filename, s.scene_index"
    
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
    if visual_match_scene_id is not None:
        ref_scene = fetch_one("""
            SELECT e.embedding as clip_embedding
            FROM scenes s
            JOIN embeddings e ON s.id = e.scene_id AND e.model_name = 'clip'
            WHERE s.id = %s
        """, (visual_match_scene_id,))
        
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
    
    # Face filter - lookup by unique face ID
    ref_emb = None

    if face_id is not None:
        ref_face = fetch_one("""
            SELECT embedding FROM faces WHERE id = %s
        """, (face_id,))
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
    
    return FileResponse(
        poster_path,
        media_type=media_type,
        # Cache for 1 year - URL includes filename param for cache-busting across re-indexes
        headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )


# ============ Video Streaming ============

@app.get("/api/video/{file_id}")
async def serve_video(file_id: int, request: Request):
    """Serve video file with HTTP range request support for streaming."""
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

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get("range")

    if range_header:
        # Parse range header: "bytes=start-end"
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1

        # Ensure valid range
        if start >= file_size:
            raise HTTPException(status_code=416, detail="Range not satisfiable")
        end = min(end, file_size - 1)
        content_length = end - start + 1

        def iter_file():
            with open(video_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 64 * 1024  # 64KB chunks
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type=media_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            }
        )

    # No range header - return full file
    return FileResponse(
        video_path,
        media_type=media_type,
        headers={"Accept-Ranges": "bytes"}
    )


# ============ Files ============

@app.get("/api/files")
async def list_files(
    limit: int = Query(50, le=500),
    offset: int = 0,
    completed: bool = Query(True, description="Only show files with completed processing")
):
    """List indexed files (shots)."""
    if completed:
        # Only show files that have completed enrichment
        files = fetch_all("""
            SELECT f.id, f.path, f.filename, f.duration_seconds, f.width, f.height,
                   f.fps, f.codec, f.audio_tracks, f.file_size_bytes,
                   f.file_created_at, f.file_modified_at, f.parent_folder,
                   f.indexed_at, f.created_at
            FROM files f
            WHERE f.deleted_at IS NULL
            AND EXISTS (
                SELECT 1 FROM enrichment_queue eq
                WHERE eq.file_id = f.id AND eq.status = 'complete'
            )
            ORDER BY f.indexed_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
    else:
        files = fetch_all("""
            SELECT id, path, filename, duration_seconds, width, height,
                   fps, codec, audio_tracks, file_size_bytes,
                   file_created_at, file_modified_at, parent_folder,
                   indexed_at, created_at
            FROM files
            WHERE deleted_at IS NULL
            ORDER BY indexed_at DESC NULLS LAST
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
    """List faces with scene info."""
    faces = fetch_all("""
        SELECT f.id, f.scene_id, s.scene_index, fi.filename
        FROM faces f
        JOIN scenes s ON f.scene_id = s.id
        JOIN files fi ON s.file_id = fi.id
        ORDER BY f.id DESC
        LIMIT %s
    """, (limit,))

    return {"faces": faces}


@app.get("/api/faces/{face_id}")
async def get_face(face_id: int):
    """Get a single face with its scene and file info."""
    face = fetch_one("""
        SELECT
            f.id,
            f.scene_id,
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


@app.get("/api/scan/progress")
async def get_scan_progress():
    """
    Get current scan progress for Reports UI.

    Returns progress info including:
    - phase: 'idle', 'discovering', 'processing', 'checking_missing', 'complete'
    - current_folder: folder being scanned (during discovery)
    - dirs_scanned: number of directories scanned
    - files_found: total video files discovered
    - files_processed: files added/checked in DB
    - files_new: newly added files
    - files_updated: modified files re-queued
    - files_skipped: inaccessible files
    - updated_at: timestamp of last progress update
    """
    row = fetch_one("SELECT value FROM config WHERE key = 'scan_progress'")
    if not row or not row.get('value'):
        return {'phase': 'idle'}
    return row['value']


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


# ============ Watch Folders ============

@app.get("/api/watch-folders")
async def get_watch_folders():
    """
    Get watch folders with accessibility status.
    Returns each folder with whether it's currently accessible.
    """
    row = fetch_one("SELECT value FROM config WHERE key = 'watch_folders'")
    folders = row['value'] if row and row.get('value') else []

    result = []
    for folder in folders:
        result.append({
            "path": folder,
            "accessible": os.path.isdir(folder)
        })

    return {"folders": result}


# ============ EDL Export ============

def seconds_to_smpte(seconds: float, fps: float = 29.97) -> str:
    """Convert seconds to SMPTE timecode (HH:MM:SS:FF)."""
    total_frames = int(round(seconds * fps))
    frames = total_frames % int(round(fps))
    total_seconds = total_frames // int(round(fps))
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"


@app.post("/api/export/edl")
async def export_edl(body: EDLExportRequest):
    """
    Export scenes as CMX 3600 EDL file.
    Accepts scene IDs with optional TC overrides.
    """
    from fastapi.responses import Response

    if not body.scenes:
        raise HTTPException(status_code=400, detail="No scenes provided")

    # Get scene info from database
    scene_ids = [s.sceneId for s in body.scenes]
    placeholders = ','.join(['%s'] * len(scene_ids))

    db_scenes = fetch_all(f"""
        SELECT
            s.id,
            s.start_tc,
            s.end_tc,
            f.filename,
            f.path,
            f.fps
        FROM scenes s
        JOIN files f ON s.file_id = f.id
        WHERE s.id IN ({placeholders})
    """, tuple(scene_ids))

    # Build lookup by scene ID
    scene_lookup = {s['id']: s for s in db_scenes}

    # Generate EDL content
    lines = [
        f"TITLE: {body.title}",
        "FCM: NON-DROP FRAME",
        ""
    ]

    record_in = 0.0  # Running record position

    for idx, item in enumerate(body.scenes, start=1):
        db_scene = scene_lookup.get(item.sceneId)
        if not db_scene:
            continue

        fps = db_scene['fps'] or 29.97
        filename = db_scene['filename']

        # Use provided TC or fall back to scene TC
        src_in = item.inTc
        src_out = item.outTc
        duration = src_out - src_in

        # Calculate record out
        record_out = record_in + duration

        # Format timecodes
        src_in_tc = seconds_to_smpte(src_in, fps)
        src_out_tc = seconds_to_smpte(src_out, fps)
        rec_in_tc = seconds_to_smpte(record_in, fps)
        rec_out_tc = seconds_to_smpte(record_out, fps)

        # EDL event line: event# reel channel transition src_in src_out rec_in rec_out
        lines.append(f"{idx:03d}  AX       V     C        {src_in_tc} {src_out_tc} {rec_in_tc} {rec_out_tc}")
        lines.append(f"* FROM CLIP NAME: {filename}")
        lines.append("")

        record_in = record_out

    edl_content = "\n".join(lines)

    # Return as downloadable file
    return Response(
        content=edl_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{body.title}.edl"'
        }
    )


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


# ============ Admin ============

DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'


@app.get("/api/admin/status")
async def admin_status():
    """Get admin status including demo mode flag."""
    return {
        "demo_mode": DEMO_MODE,
        "admin_enabled": not DEMO_MODE
    }


@app.post("/api/admin/reset-failed-jobs")
async def reset_failed_jobs():
    """Reset all failed enrichment jobs to pending status."""
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="Admin actions disabled in demo mode")

    result = execute(
        "UPDATE enrichment_queue SET status = 'pending', error = NULL WHERE status = 'failed'"
    )
    count = result.rowcount if hasattr(result, 'rowcount') else 0
    return {"success": True, "reset_count": count}


@app.post("/api/admin/reset-processing-jobs")
async def reset_processing_jobs():
    """Reset stuck processing jobs to pending status."""
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="Admin actions disabled in demo mode")

    result = execute(
        "UPDATE enrichment_queue SET status = 'pending', started_at = NULL WHERE status = 'processing'"
    )
    count = result.rowcount if hasattr(result, 'rowcount') else 0
    return {"success": True, "reset_count": count}


@app.post("/api/admin/purge-deleted")
async def purge_deleted_files():
    """Permanently remove soft-deleted files and their data."""
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="Admin actions disabled in demo mode")

    # Count first
    count_row = fetch_one("SELECT COUNT(*) as count FROM files WHERE deleted_at IS NOT NULL")
    count = count_row['count'] if count_row else 0

    # Delete (cascades to scenes, faces, embeddings, queue)
    execute("DELETE FROM files WHERE deleted_at IS NOT NULL")

    return {"success": True, "purged_count": count}


@app.post("/api/admin/purge-orphans")
async def purge_orphan_files():
    """Remove files not under any current watch folder."""
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="Admin actions disabled in demo mode")

    # Get current watch folders
    row = fetch_one("SELECT value FROM config WHERE key = 'watch_folders'")
    watch_folders = row['value'] if row and row.get('value') else []

    if not watch_folders:
        return {"success": True, "purged_count": 0, "message": "No watch folders configured"}

    # Build condition to find files NOT in any watch folder
    conditions = " AND ".join([f"path NOT LIKE %s" for _ in watch_folders])
    params = [f"{folder}%" for folder in watch_folders]

    # Count orphans
    count_row = fetch_one(
        f"SELECT COUNT(*) as count FROM files WHERE {conditions}",
        tuple(params)
    )
    count = count_row['count'] if count_row else 0

    if count > 0:
        execute(f"DELETE FROM files WHERE {conditions}", tuple(params))

    return {"success": True, "purged_count": count}


@app.delete("/api/admin/database")
async def wipe_database():
    """Wipe all indexed data. Dangerous!"""
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="Admin actions disabled in demo mode")

    # Get counts before wiping
    files_count = fetch_one("SELECT COUNT(*) as count FROM files")['count']
    scenes_count = fetch_one("SELECT COUNT(*) as count FROM scenes")['count']
    faces_count = fetch_one("SELECT COUNT(*) as count FROM faces")['count']

    # Truncate all data tables (preserves config)
    execute("TRUNCATE files, scenes, faces, enrichment_queue, embeddings RESTART IDENTITY CASCADE")

    return {
        "success": True,
        "wiped": {
            "files": files_count,
            "scenes": scenes_count,
            "faces": faces_count
        }
    }


@app.post("/api/admin/restart-server")
async def restart_server():
    """
    Restart the server process to refresh media mount points.
    Used when external drives are remounted.
    """
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="Admin actions disabled in demo mode")

    import sys
    import asyncio

    async def delayed_exit():
        await asyncio.sleep(0.5)  # Give time for response to be sent
        sys.exit(0)  # Exit cleanly; Docker will restart the container

    asyncio.create_task(delayed_exit())
    return {"success": True, "message": "Server restarting..."}
