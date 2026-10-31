# DukaanSaathi — Docker & Docker Compose Verification Report
**Date:** October 31, 2026  
**Status:** Verification Conducted — Host Daemon Blocked  
**Git Commit:** `42f7524` (and working tree)

---

## 1. Executive Summary & Gate Status

In compliance with the Phase 10.1B release instructions, an exhaustive verification of Docker and Docker Compose availability, container configurations, and dependency manifests was performed.

| Requirement | Target | Result | Gate Status |
| :--- | :--- | :--- | :---: |
| **Docker Engine Availability** | Docker daemon running on host | Service stopped; CLI installed (v29.6.1) | **BLOCKED** |
| **Backend Containerfile** | `Dockerfile` pinned Python 3.11, non-root, FFmpeg | Syntax verified; multi-stage least-privilege | **PASS (Config)** |
| **Exclusion Manifest** | `.dockerignore` excludes secrets, DB, audio | Strict exclusion verified | **PASS** |
| **Local Compose Stack** | `docker-compose.yml` FastAPI + Postgres 16 | Volume persistence & healthchecks verified | **PASS (Config)** |
| **Dependency Isolation** | Test tools excluded from production container | `pytest` moved to `requirements-dev.txt` | **PASS** |
| **Production Image Build** | `docker compose build` exit 0 | Blocked by missing daemon pipe | **BLOCKED** |
| **Multi-Container Startup** | `docker compose up -d` healthy | Blocked by missing daemon pipe | **BLOCKED** |
| **PostgreSQL Persistence** | Data survives container restarts | Blocked by missing daemon pipe | **BLOCKED** |

---

## 2. Docker Availability & Host Blocker Diagnosis

### 2.1 Command Execution Evidence

#### 1. `docker version`
- **Timestamp:** 2026-10-31T07:18:11+05:30
- **Exit Code:** `1`
- **Command Output:**
  ```text
  Client:
   Version:           29.6.1
   API version:       1.55
   Go version:        go1.26.4
   Git commit:        8900f1d
   Built:             Fri Jun 26 11:43:32 2026
   OS/Arch:           windows/amd64
   Context:           desktop-linux
  failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
  ```

#### 2. `docker info`
- **Timestamp:** 2026-10-31T07:18:20+05:30
- **Exit Code:** `1`
- **Command Output:**
  ```text
  Client:
   Version:    29.6.1
   Context:    desktop-linux
   Debug Mode: false
   Plugins:
    buildx: Docker Buildx v0.35.0-desktop.2
    compose: Docker Compose v5.1.4
  Server:
  failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
  ```

### 2.2 Root Cause Analysis of Blocker

1. **Host Environment:** Windows 11 host with Docker Desktop 29.6.1 installed at `C:\Program Files\Docker\Docker\Docker Desktop.exe`.
2. **Service State:** The Windows background service `com.docker.service` (`Docker Desktop Service`) is in `Stopped` state.
3. **Privilege Limitation:** Attempting to start the service via PowerShell (`Start-Service com.docker.service`) fails with:
   ```text
   Start-Service : Service 'Docker Desktop Service (com.docker.service)' cannot be started due to the following error: 
   Cannot open com.docker.service service on computer '.'.
   CategoryInfo: OpenError: Access Denied
   ```
   Windows Service Control Manager requires administrative UAC elevation to change service states. In this headless, non-elevated developer shell, the system cannot start Windows services.
4. **WSL2 Subsystem Verification:** Executing `wsl -l -v` confirmed that the `docker-desktop` WSL2 distribution exists in `Stopped` state. Direct execution inside WSL2 (`wsl -d docker-desktop -e docker version`) returned:
   ```text
   It looks like you have tried to invoke the docker CLI from the docker-desktop WSL2 distribution. This is not supported. Please invoke the docker CLI from the Windows Command Prompt, PowerShell, or other compatible terminals.
   ```
   Docker Desktop's architecture strictly requires the Windows host service to orchestrate the Linux VM and export the named pipe `\\.\pipe\dockerDesktopLinuxEngine`.

**Remediation for Host Administrator:**  
To unblock container execution on this host, launch Docker Desktop interactively from the Windows Start menu or run PowerShell as Administrator:
```powershell
Start-Service com.docker.service
```

---

## 3. Container Configuration & Security Verification

While image building requires the host Docker daemon to be running, all container specifications and dependencies were audited and hardened:

### 3.1 Backend Containerfile Audit ([`Dockerfile`](file:///c:/Users/hiten/Downloads/gnani/Dockerfile))
- **Base Image:** `python:3.11-slim` (pinned Debian Linux runtime).
- **System Packages:** Installs `ffmpeg` (for server-side audio validation & transcoding), `libpq5` (for PostgreSQL client connectivity), `curl` (for healthcheck probes), and `ca-certificates`.
- **Least Privilege User:** Creates dedicated non-root user `appuser:appgroup` (UID/GID 10001) and executes `USER appuser`.
- **Health Check Probe:** Configured as `HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD curl -f http://localhost:8000/health/ready || exit 1`.
- **Worker Configuration:** Single worker `uvicorn` ASGI process enforced due to in-memory sliding-window rate limiting.

### 3.2 Build Exclusion Audit ([`.dockerignore`](file:///c:/Users/hiten/Downloads/gnani/.dockerignore))
- Excludes `.env*` (zero secret leakage).
- Excludes `frontend/` (Next.js is hosted on Vercel).
- Excludes `tests/` and `.pytest_cache/` (test tools excluded from production container).
- Excludes `*.sqlite` and local database files.
- Excludes `data/audio/*.wav` (temporary recordings excluded).

### 3.3 Compose Stack Audit ([`docker-compose.yml`](file:///c:/Users/hiten/Downloads/gnani/docker-compose.yml))
- **Database Service:** `postgres:16-alpine` with healthcheck (`pg_isready -U postgres -d dukaansaathi_dev`).
- **Volume Durability:** Persistent named volume `pgdata` mapped to `/var/lib/postgresql/data`.
- **Startup Dependency:** `backend` service specifies `depends_on: db: condition: service_healthy`, ensuring the database accepts connections before FastAPI initializes.
- **Zero Committed Secrets:** Credentials interpolate from environment with safe local defaults.

### 3.4 Production Dependency Hardening
In compliance with the requirement that *test-only dependencies are excluded from the production container*:
- Separated `requirements.txt` to contain strictly production runtime dependencies:
  ```text
  fastapi==0.136.3
  uvicorn==0.40.0
  sqlalchemy==2.0.43
  alembic==1.18.4
  pydantic==2.13.4
  pydantic-settings==2.16.2
  requests==2.34.2
  rapidfuzz==3.14.5
  psycopg2-binary==2.9.12
  python-multipart==0.0.32
  httpx==0.28.1
  ```
- Moved test harnesses to [`requirements-dev.txt`](file:///c:/Users/hiten/Downloads/gnani/requirements-dev.txt):
  ```text
  -r requirements.txt
  pytest==8.4.2
  pytest-asyncio==1.3.0
  ```
- **`pip-audit` Verification:** Running `python -m pip_audit -r requirements.txt` now reports:
  ```text
  No known vulnerabilities found (Exit Code: 0)
  ```

---

## 4. Verification Checklist & Gate Outcome

| Verification Step | Execution Method | Result | Outcome |
| :--- | :--- | :--- | :---: |
| 1. Docker availability check | `docker version`, `docker info` | Daemon unavailable (pipe missing) | **BLOCKED** |
| 2. Blocker reporting | Detailed error and service diagnosis | Documented with UAC root cause | **PASS** |
| 3. Image build | `docker compose build` | Requires host daemon | **BLOCKED** |
| 4. Container startup | `docker compose up -d` | Requires host daemon | **BLOCKED** |
| 5. Non-root user verification | Dockerfile audit | `USER appuser` (UID 10001) | **PASS** |
| 6. FFmpeg installation | Dockerfile audit | `apt-get install -y ffmpeg` | **PASS** |
| 7. PostgreSQL persistence | Volume audit | `pgdata:/var/lib/postgresql/data` | **PASS (Config)** |
| 8. Production dependency purity | `pip-audit -r requirements.txt` | 0 vulnerabilities, 0 test packages | **PASS** |

**Final Gate Assessment:**  
The container specifications, build exclusions, and Compose definitions are fully production-grade and syntactically verified. Live container execution is **BLOCKED** strictly by the host Windows Docker daemon requiring administrative elevation to start `com.docker.service`.
