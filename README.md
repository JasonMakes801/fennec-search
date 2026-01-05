<p align="center">
  <img src="ui/public/fennec-logo-lg.png" alt="Fennec Logo" width="120">
</p>

<h1 align="center">Fennec Search</h1>

<p align="center">
  <strong>Self-hosted video search using natural language, faces, and spoken dialog.</strong>
</p>

<p align="center">
  <a href="https://fennec.jasongpeterson.com"><strong>Live Demo</strong></a>
</p>

Find any moment in your media library. Fennec enriches your videos with AI models (CLIP, Whisper, ArcFace) and stores embeddings in Postgres with pgvector for fast similarity search.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-required-blue.svg)

---

## Features

- **Natural Language Search** — Describe what you're looking for ("person walking outdoors at sunset")
- **Dialog Search** — Find moments by what was said (Whisper transcription)
- **Face Search** — Find all appearances of a person across your library
- **Scene Detection** — Automatic scene boundary detection with poster frames
- **Self-Hosted** — Runs entirely on your hardware, no cloud required
- **Docker-Based** — One command to start everything

---

## Quick Start

### Prerequisites

- Docker (macOS or Linux)
- ~10GB disk space for ML models (downloaded on first run)

> **Linux deployment:** See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup with SSL.

### 1. Clone and Start

```bash
git clone https://github.com/JasonMakes801/fennec-search.git
cd fennec-search
```

### 2. Configure Watch Folders

Edit `docker-compose.yml` and set the `WATCH_FOLDERS` environment variable for the ingest service:

```yaml
ingest:
  environment:
    WATCH_FOLDERS: /Users/yourname/Videos,/Volumes/NAS/Media
```

Multiple folders can be comma-separated. These paths must be accessible inside the container via the volume mounts (see the media volumes section in the compose file).

### 3. Start Services

```bash
docker compose up -d
```

> **Build time:** First build takes **10-15 minutes** to download and install PyTorch, transformers, and other ML libraries (~2GB). Subsequent builds use Docker's cache and complete in seconds.
>
> **First run:** When you process your first video, ML models (~1GB total) download automatically: CLIP for visual search, Whisper for transcription, ArcFace for faces. This adds ~2-3 minutes on first use, then models are cached.

### 4. Start Searching

Open **http://localhost:8080**. The ingest service will automatically scan and enrich your videos. Search results appear as files are processed.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│       UI        │────▶│     Server      │────▶│    Postgres     │
│   (Vue + Vite)  │     │    (FastAPI)    │     │   + pgvector    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        ▲
                        ┌─────────────────┐             │
                        │  Ingest Service │─────────────┘
                        │   (CLIP/Whisper │
                        │    /ArcFace)    │
                        └─────────────────┘
```

| Container | Port | Description |
|-----------|------|-------------|
| `fennec-ui` | 8080 | Web interface |
| `fennec-server` | 8000 | FastAPI backend |
| `fennec-db` | 5432 | PostgreSQL + pgvector |
| `fennec-ingest` | — | Background enrichment service |

---

## Common Commands

### Start/Stop

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f
```

### Restart Individual Services

```bash
# Restart the backend (after code changes)
docker restart fennec-server

# Restart the UI
docker restart fennec-ui

# Restart the ingest service
docker restart fennec-ingest

# Rebuild and restart (after Dockerfile changes)
docker compose up --build -d
```

### Pause/Resume Indexing

```bash
# Pause the indexer
docker exec fennec-db psql -U fennec -c \
  "UPDATE config SET value = '\"paused\"' WHERE key = 'indexer_state';"

# Resume the indexer
docker exec fennec-db psql -U fennec -c \
  "UPDATE config SET value = '\"running\"' WHERE key = 'indexer_state';"
```

### Re-process All Files

```bash
# Clear enrichment data and re-queue everything
docker exec fennec-db psql -U fennec -c \
  "DELETE FROM faces; DELETE FROM scenes; UPDATE enrichment_queue SET status = 'pending', started_at = NULL, completed_at = NULL;"
```

### Check Stats

```bash
docker exec fennec-db psql -U fennec -c \
  "SELECT COUNT(*) as files FROM files; SELECT COUNT(*) as scenes FROM scenes; SELECT COUNT(*) as faces FROM faces;"
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | fennec | Database user |
| `POSTGRES_PASSWORD` | fennec | Database password |
| `POSTGRES_DB` | fennec | Database name |

### Watch Folders

Mount your media directories in `docker-compose.yml`:

```yaml
volumes:
  - /path/to/your/videos:/media:ro
```

Then add the path via the UI Settings page or:

```bash
docker exec fennec-db psql -U fennec -c \
  "UPDATE config SET value = '[\"/media\"]' WHERE key = 'watch_folders';"
```

### Model Settings

Toggle which models run during enrichment:

```bash
# Disable face detection (faster processing)
docker exec fennec-db psql -U fennec -c \
  "UPDATE config SET value = '{\"clip\": true, \"whisper\": true, \"arcface\": false}' WHERE key = 'enrichment_models';"
```

---

## Troubleshooting

### Ingest service not finding files

1. Check that the path is mounted in `docker-compose.yml`
2. Verify the watch folder is configured: `docker exec fennec-db psql -U fennec -c "SELECT value FROM config WHERE key = 'watch_folders';"`
3. Check ingest logs: `docker logs fennec-ingest -f`

### Search not returning results

1. Wait for enrichment to complete (check queue status in Settings)
2. Ensure scenes have embeddings: `docker exec fennec-db psql -U fennec -c "SELECT COUNT(*) FROM embeddings WHERE model_name = 'clip';"`

### Out of memory during enrichment

Models run on CPU by default. For large files, you may need to increase Docker's memory limit or process files in smaller batches.

---

## Known Limitations

### Browser Video Playback

Scene previews may briefly flash frames from adjacent scenes when seeking or at scene boundaries. This is a limitation of HTML5 video—browsers display the nearest keyframe while decoding the requested frame. For frame-accurate review, export clips to an NLE.

---

## Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Frontend**: Vue 3, Vite, Tailwind CSS
- **Database**: PostgreSQL 16 + pgvector
- **ML Models**:
  - CLIP (ViT-B-32) — Visual embeddings
  - Whisper (base) — Speech transcription
  - all-MiniLM-L6-v2 — Transcript embeddings for semantic dialog search
  - ArcFace (buffalo_l) — Face detection & recognition
- **Video Processing**: FFmpeg, PySceneDetect

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Roadmap

- [x] Linux support
- [ ] GPU acceleration
- [ ] Additional embedding models
- [ ] Batch export/import
- [ ] API authentication
- [ ] Face naming/labeling UI

---

**Find any moment by what it looks like, what was said, or who's in it.**

Powered by [OpenCLIP](https://github.com/mlfoundations/open_clip) and [sentence-transformers](https://www.sbert.net/). 🦊
