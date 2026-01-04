"""
Transcript embedding for semantic dialog search.
Uses sentence-transformers (all-MiniLM-L6-v2) with MPS on Apple Silicon, CPU fallback.
Enables semantic matching: "1" ↔ "one", "car" ↔ "vehicle", etc.
"""

import torch
from sentence_transformers import SentenceTransformer
from db import get_connection

# Model config
MODEL_NAME = 'all-MiniLM-L6-v2'
MODEL_VERSION = 'all-MiniLM-L6-v2'
EMBEDDING_DIM = 384

# Global model (loaded once)
_model = None


def get_device():
    """Get best available device (MPS on Apple Silicon, else CPU)."""
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model():
    """Load sentence-transformer model. Downloads on first run (~80MB)."""
    global _model

    if _model is not None:
        return _model

    device = get_device()
    print(f"    Loading sentence-transformer model on {device} (first run downloads ~80MB)...")
    _model = SentenceTransformer(MODEL_NAME, device=device)
    print(f"    ✓ Sentence-transformer model loaded on {device}")

    return _model


def embed_transcript(text):
    """
    Embed a transcript string.
    Returns normalized 384-dim vector.
    """
    if not text or not text.strip():
        return None
    
    model = load_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_transcripts_for_file(file_id):
    """
    Embed all transcripts for scenes in a file.
    Only processes scenes that have transcripts but no transcript embedding yet.
    Returns number of scenes embedded.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Get scenes with transcripts that don't have transcript embeddings
    cur.execute("""
        SELECT s.id, s.transcript
        FROM scenes s
        LEFT JOIN embeddings e ON s.id = e.scene_id AND e.model_name = 'sentence-transformer'
        WHERE s.file_id = %s 
        AND s.transcript IS NOT NULL 
        AND s.transcript != ''
        AND e.id IS NULL
    """, (file_id,))
    
    scenes = cur.fetchall()
    
    if not scenes:
        print("    ⏭️  No transcripts to embed")
        cur.close()
        conn.close()
        return 0
    
    # Load model once for all scenes
    model = load_model()
    
    embedded_count = 0
    for scene_id, transcript in scenes:
        if not transcript or not transcript.strip():
            continue
        
        # Generate embedding
        embedding = model.encode(transcript, normalize_embeddings=True)
        
        # Store in embeddings table
        cur.execute("""
            INSERT INTO embeddings (scene_id, model_name, model_version, dimension, embedding)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (scene_id, model_name) 
            DO UPDATE SET embedding = EXCLUDED.embedding, 
                          model_version = EXCLUDED.model_version,
                          created_at = NOW()
        """, (scene_id, 'sentence-transformer', MODEL_VERSION, EMBEDDING_DIM, embedding.tolist()))
        
        embedded_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    device = get_device()
    print(f"    ✓ Embedded {embedded_count} transcript(s) on {device.upper()}")
    return embedded_count
