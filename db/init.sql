-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Files table
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    filename TEXT,
    
    -- Video metadata (from FFprobe)
    duration_seconds FLOAT,
    width INTEGER,
    height INTEGER,
    fps FLOAT,
    codec TEXT,
    audio_tracks INTEGER DEFAULT 0,
    
    -- Color metadata (from FFprobe)
    pix_fmt TEXT,           -- yuv420p, yuv420p10le, etc.
    color_space TEXT,       -- bt709, bt2020nc, etc.
    color_transfer TEXT,    -- bt709, smpte2084 (HDR10), arib-std-b67 (HLG)
    color_primaries TEXT,   -- bt709, bt2020
    
    -- File metadata
    file_size_bytes BIGINT,
    file_created_at TIMESTAMP,      -- From filesystem
    file_modified_at TIMESTAMP,     -- From filesystem
    parent_folder TEXT,             -- Immediate parent directory name
    
    -- User metadata
    tags JSONB DEFAULT '[]'::jsonb, -- User-defined tags ["interview", "b-roll"]
    
    -- Index state
    created_at TIMESTAMP DEFAULT NOW(),  -- When added to DB
    indexed_at TIMESTAMP,                 -- When enrichment completed
    deleted_at TIMESTAMP                  -- Soft delete (file disappeared)
);

-- Scenes (soft cuts from scene detection)
CREATE TABLE scenes (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    scene_index INTEGER,
    start_tc FLOAT,
    end_tc FLOAT,
    poster_frame_path TEXT,      -- Center frame (for thumbnails + player initial display)
    transcript TEXT,             -- Whisper transcript (stored here for full-text search)
    clip_cluster_id INTEGER,     -- HDBSCAN cluster assignment (-1 = noise/unclustered)
    clip_cluster_order FLOAT     -- Distance to cluster centroid (for sorting within cluster)
);

-- Embeddings (model-versioned vectors for search)
-- Supports multiple models with different dimensions
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,       -- e.g., 'clip', 'whisper', 'clap'
    model_version TEXT NOT NULL,    -- e.g., 'ViT-B-32-laion2b_s34b_b79k', 'base'
    dimension INTEGER NOT NULL,     -- Vector dimension (512, 768, 1024, etc.)
    embedding vector,               -- Variable dimension vector
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- One embedding per scene per model (new version overwrites old)
    UNIQUE (scene_id, model_name)
);

-- Faces (ArcFace embeddings with bounding boxes)
CREATE TABLE faces (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id) ON DELETE CASCADE,
    embedding vector(512),  -- ArcFace (fixed 512-dim)
    cluster_id INTEGER,     -- HDBSCAN cluster assignment (-1 = noise/unclustered)
    cluster_order FLOAT,    -- Distance to cluster centroid (for sorting within cluster)
    bbox_x FLOAT,
    bbox_y FLOAT,
    bbox_w FLOAT,
    bbox_h FLOAT
);

-- Enrichment queue
CREATE TABLE enrichment_queue (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',  -- pending, processing, complete, failed
    queued_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    -- Stage progress tracking
    current_stage TEXT,             -- 'scene_detection', 'clip', 'whisper', 'arcface'
    current_stage_num INTEGER,      -- 1, 2, 3, 4
    total_stages INTEGER            -- Total stages for this file (based on enabled models)
);

-- Config (watch folders, settings)
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value JSONB
);

-- Insert default config
INSERT INTO config (key, value) VALUES 
    ('indexer_state', '"running"'),      -- running, paused
    ('last_scan_at', 'null'),
    ('last_scan_duration_ms', 'null'),
    ('poll_interval_seconds', '3600'),   -- 1 hour default
    ('watch_folders', '[]'),
    ('enrichment_models', '{"clip": true, "whisper": true, "arcface": true}'),
    ('poster_width', '1280'),            -- 720p width
    ('poster_format', '"webp"'),
    ('poster_quality', '80'),
    -- Search threshold defaults (cosine similarity, 0-1 range)
    ('search_threshold_visual', '0.10'),       -- CLIP text-to-image search
    ('search_threshold_visual_match', '0.20'), -- Scene-to-scene visual similarity
    ('search_threshold_face', '0.25'),         -- ArcFace similarity
    -- Model registry (versions for partial enrichment)
    ('model_versions', '{
        "clip": {"version": "ViT-B-32-laion2b_s34b_b79k", "dimension": 512},
        "whisper": {"version": "base", "dimension": 512}
    }');

-- Index for embeddings by model (partial indexes for each model type)
-- Note: IVFFlat indexes should be created after data exists for optimal list sizing
CREATE INDEX idx_embeddings_scene ON embeddings (scene_id);
CREATE INDEX idx_embeddings_model ON embeddings (model_name);

-- Index for face similarity search
CREATE INDEX ON faces USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for scene clustering
CREATE INDEX idx_scenes_clip_cluster ON scenes (clip_cluster_id);

-- Index for queue processing
CREATE INDEX ON enrichment_queue (status, queued_at);
