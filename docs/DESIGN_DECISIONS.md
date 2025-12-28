# Design Decisions

## 1. First Frame Extraction (Simplified)

**Decision:** Remove first-frame extraction. Use center frame (poster frame) for player initial display.

**Rationale:**
- First frame extraction was added to compensate for imprecise frame seeking in the HTML5 video player
- The extra frame doubles poster storage and extraction time
- Center frame provides a good visual cue of what the scene contains
- First/last frames of scenes may be imprecisely returned by the player, but this is acceptable as a known limitation

**Implementation:**
1. Remove `poster_first_path` column from `scenes` table
2. Remove first frame extraction from `scene_detect.py`
3. Modify player in `Search.vue`:
   - Show center frame (`poster_frame_path`) with play button overlay initially
   - On play button click, start video playback from `start_tc`
   - Accept imprecise seeking at scene boundaries as known limitation
4. Remove `/api/first-frame/` endpoint (use existing `/api/thumbnail/`)

**Known Limitation:** Scene boundaries may not be frame-accurate due to HTML5 video seek behavior. Users will see approximately the correct content.

---

## 2. Vector Model Versioning (Partial Enrichment)

**Decision:** Label all embeddings with model name and version to support incremental enrichment.

**Rationale:**
- Allow adding new models (e.g., CLAP for audio) without re-processing existing vectors
- Support model version upgrades that overwrite old embeddings from same model
- Display vector types in UI for transparency and debugging
- Future-proof for multi-model search strategies

**New Schema:**

```sql
-- Replaces embedded columns (clip_embedding, transcript_embedding)
-- Supports variable dimensions per model
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    scene_id INTEGER REFERENCES scenes(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,       -- e.g., 'clip', 'whisper', 'clap'
    model_version TEXT NOT NULL,    -- e.g., 'ViT-B-32-laion2b_s34b_b79k', 'base'
    dimension INTEGER NOT NULL,     -- Vector dimension (512, 768, 1024, etc.)
    embedding vector,               -- Variable dimension vector (no fixed size)
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint: one embedding per scene per model
    -- New version overwrites old version of same model
    UNIQUE (scene_id, model_name)
);

-- Partial indexes per model for similarity search
-- These must be created AFTER data exists (pgvector requires rows to infer dimension)
-- Or created dynamically when a new model is first used
-- Example for 512-dim models:
-- CREATE INDEX idx_embeddings_clip ON embeddings 
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100) 
--     WHERE model_name = 'clip';
```

**Note on pgvector indexes:** IVFFlat indexes require all vectors in the index to have the same dimension. By using partial indexes (`WHERE model_name = 'X'`), each model gets its own index with its own dimension. Indexes should be created after initial data load for best list tuning.

**Model Registry (in config table):**

```json
{
  "models": {
    "clip": {
      "version": "ViT-B-32-laion2b_s34b_b79k",
      "dimension": 512,
      "enabled": true
    },
    "whisper": {
      "version": "base",
      "dimension": 512,
      "enabled": true
    },
    "clap": {
      "version": "laion/larger_clap_music_and_speech",
      "dimension": 512,
      "enabled": false
    }
  }
}
```

**Face embeddings** remain in the `faces` table (bbox data, multiple per scene). ArcFace is not in the embeddings table.

**Enrichment Logic:**
1. For each enabled model in registry:
   - Check if scene already has embedding for this model+version
   - If missing or version differs: generate new embedding
   - UPSERT into embeddings table (overwrites old version)
2. Old vectors from disabled models are preserved (not deleted)
3. Re-enrichment of a model wipes old version, writes new

**UI Display:**

*Report Page - Vector Types per Shot:*
```
Vector Coverage:
├── CLIP (ViT-B-32, 512d): 155/155 scenes (100%)
├── Whisper (base, 512d): 142/155 scenes (92%)
└── Faces: 93 detected across 47 scenes
```

*Player Shot Info Section:*
```
Vectors:
• CLIP ViT-B-32 (512d) ✓
• Whisper base (512d) ✓
• 3 faces detected
```

**Data Reset:** Since we're changing the schema fundamentally, existing data will be cleared. Run re-enrichment after schema migration.

---

## Notes

- Faces table remains separate (multiple faces per scene with bbox data, ArcFace embeddings)
- Transcript text stays in scenes table (for full-text search), only embedding moves
- Variable dimension support means we can add models like CLIP ViT-L (768d) or larger whisper models
- Indexes created per-model to handle different dimensions
