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
    poster_first_path TEXT,      -- First frame (for player initial display)
    poster_frame_path TEXT,      -- Mid frame (for thumbnails + CLIP embedding)
    clip_embedding vector(512),  -- CLIP ViT-B-32
    transcript TEXT,
    transcript_embedding vector(512)
);

-- Faces
CREATE TABLE faces (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id) ON DELETE CASCADE,
    embedding vector(512),  -- ArcFace
    cluster_id INTEGER,
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
    retry_count INTEGER DEFAULT 0
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
    ('search_threshold_face', '0.25');         -- ArcFace similarity

-- Create indexes for vector similarity search
CREATE INDEX ON scenes USING ivfflat (clip_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON faces USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index for queue processing
CREATE INDEX ON enrichment_queue (status, queued_at);
