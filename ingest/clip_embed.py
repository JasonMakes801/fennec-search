"""
CLIP embedding generation for visual search.
Uses OpenCLIP with ViT-B-32 model (CPU inference).
"""

import open_clip
import torch
from PIL import Image
from db import get_connection
from progress import progress_counter, progress_done

# Global model (loaded once)
_model = None
_preprocess = None
_tokenizer = None


def load_model():
    """Load CLIP model (ViT-B-32). Downloads on first run (~400MB)."""
    global _model, _preprocess, _tokenizer
    
    if _model is not None:
        return _model, _preprocess, _tokenizer
    
    print("    Loading CLIP model (first run downloads ~400MB)...")
    
    _model, _, _preprocess = open_clip.create_model_and_transforms(
        'ViT-B-32',
        pretrained='laion2b_s34b_b79k'
    )
    _tokenizer = open_clip.get_tokenizer('ViT-B-32')
    
    _model.eval()  # Set to evaluation mode
    
    print("    ✓ CLIP model loaded")
    return _model, _preprocess, _tokenizer


def embed_image(image_path):
    """
    Generate CLIP embedding for an image.
    Returns a 512-dim numpy array.
    """
    model, preprocess, _ = load_model()
    
    image = Image.open(image_path).convert('RGB')
    image_tensor = preprocess(image).unsqueeze(0)
    
    with torch.no_grad():
        embedding = model.encode_image(image_tensor)
        # Normalize embedding
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    
    return embedding.squeeze().numpy()


def embed_text(text):
    """
    Generate CLIP embedding for text query.
    Returns a 512-dim numpy array.
    """
    model, _, tokenizer = load_model()
    
    tokens = tokenizer([text])
    
    with torch.no_grad():
        embedding = model.encode_text(tokens)
        # Normalize embedding
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    
    return embedding.squeeze().numpy()


def embed_scenes_for_file(file_id):
    """
    Generate CLIP embeddings for all scenes of a file.
    Updates the clip_embedding column in scenes table.
    Returns number of scenes embedded.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Get scenes with poster frames but no embedding yet
    cur.execute("""
        SELECT id, poster_frame_path 
        FROM scenes 
        WHERE file_id = %s 
        AND poster_frame_path IS NOT NULL
        AND clip_embedding IS NULL
    """, (file_id,))
    
    scenes = cur.fetchall()
    
    if not scenes:
        cur.close()
        conn.close()
        return 0
    
    total = len(scenes)
    
    for i, (scene_id, poster_path) in enumerate(scenes, 1):
        progress_counter(i, total, "CLIP embedding")
        try:
            embedding = embed_image(poster_path)
            embedding_list = embedding.tolist()
            cur.execute(
                "UPDATE scenes SET clip_embedding = %s WHERE id = %s",
                (embedding_list, scene_id)
            )
        except Exception as e:
            pass  # Skip failed embeddings silently
    
    conn.commit()
    cur.close()
    conn.close()
    
    progress_done(f"Embedded {total} scenes")
    return total
