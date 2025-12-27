<p align="center">
  <img src="ui/public/fennec-logo-lg.png" alt="Fennec Logo" width="120">
</p>

<h1 align="center">Fennec</h1>

<p align="center">
  <strong>Self-hosted video search using natural language, faces, and spoken dialog.</strong>
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

- Docker & Docker Compose
- ~10GB disk space for ML models (downloaded on first run)

### 1. Clone and Start

```bash
git clone https://github.com/JasonMakes801/fennec-search.git
cd fennec-search
cp .env.example .env
docker compose up -d
```

### 2. Configure Watch Folders

Open the UI at **http://localhost:8080** and go to **Settings** to add folders containing your videos.

Or via command line:
```bash
docker exec fennec-db psql -U fennec -c \
  "UPDATE config SET value = '[\"/path/to/your/videos\"]' WHERE key = 'watch_folders';"
```

### 3. Start Searching

The ingest service will automatically scan and enrich your videos. Search results appear as files are processed.

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
2. Ensure scenes have embeddings: `docker exec fennec-db psql -U fennec -c "SELECT COUNT(*) FROM scenes WHERE clip_embedding IS NOT NULL;"`

### Out of memory during enrichment

Models run on CPU by default. For large files, you may need to increase Docker's memory limit or process files in smaller batches.

---

## Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Frontend**: Vue 3, Vite, Tailwind CSS
- **Database**: PostgreSQL 16 + pgvector
- **ML Models**: 
  - CLIP (ViT-B-32) — Visual embeddings
  - Whisper (base) — Speech transcription
  - ArcFace (buffalo_l) — Face detection & recognition
- **Video Processing**: FFmpeg, PySceneDetect

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Roadmap

- [ ] GPU acceleration support
- [ ] Additional embedding models
- [ ] Batch export/import
- [ ] API authentication
- [ ] Face naming/labeling UI

---

**Built for anyone with too much video who can't or won't use cloud services.** 🦊
