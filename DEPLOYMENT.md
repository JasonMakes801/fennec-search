# Fennec Search Deployment Guide

**Live Demo:** https://fennec.jasongpeterson.com

## Local Development (macOS)

1. Edit `docker-compose.yml`:
   - Set `WATCH_FOLDERS` to your media path
   - Volume mounts for `/Users` and `/Volumes` are pre-configured

2. Run:
   ```bash
   docker compose up
   ```

3. Access at http://localhost:8080

## Linux Production Deployment

### 1. Prepare Your Server

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone the repo
git clone https://github.com/YourUser/fennec-search.git
cd fennec-search
```

### 2. Configure Paths

Edit `docker-compose.prod.yml`:

```yaml
# In the ingest service:
WATCH_FOLDERS: /mnt/media/          # Your media path
volumes:
  - /mnt/media:/mnt/media:ro        # Mount your media

# In the server service:
volumes:
  - /mnt/media:/mnt/media:ro        # Same mount
```

### 3. Run Without SSL

For testing or internal use:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Access at http://your-server-ip:8080

### 4. Add SSL (Optional)

For public deployments with your own domain:

**a. Get SSL certificates:**
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
```

**b. Edit `ui/nginx.prod.conf`:**
- Replace `fennec.jasongpeterson.com` with your domain

**c. Edit `docker-compose.prod.yml` ui service:**
```yaml
ui:
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
    - ./ui/nginx.prod.conf:/etc/nginx/conf.d/default.conf:ro
```

**d. Rebuild and restart:**
```bash
docker compose -f docker-compose.prod.yml up -d --build ui
```

## Updating

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Common Issues

**Container won't start:** Check logs with `docker logs fennec-server`

**Media not found:** Ensure volume mount paths match `WATCH_FOLDERS`

**Thumbnails not loading:** Run `docker compose -f docker-compose.prod.yml restart`
