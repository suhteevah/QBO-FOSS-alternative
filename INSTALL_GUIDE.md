# OpenLedger — Installation Guide

> **Repo:** https://github.com/suhteevah/QBO-FOSS-alternative

---

## Quick Start (One-Liner)

### Linux / macOS
```bash
curl -fsSL https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.sh | bash
```
or with wget:
```bash
wget -qO- https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.sh | bash
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.ps1 | iex
```

### What the bootstrap does:
1. Detects your environment (Docker, Python, Node)
2. **Auto-installs Docker** if not found:
   - Linux: official `get.docker.com` script
   - macOS: `brew install --cask docker`
   - Windows: `winget install Docker.DockerDesktop` (fallback: Chocolatey)
3. Clones the repository
4. Runs the appropriate installer (Docker or dev/SQLite)
5. Starts the app and opens your browser

### Environment Variables (Optional)
```bash
# Force a specific mode
OPENLEDGER_MODE=docker  # or "dev"
OPENLEDGER_DIR=./mydir  # custom install directory
```

---

## Method 1: Docker (Production)

### Prerequisites
- Docker + Docker Compose
- Git

### Steps
```bash
git clone https://github.com/suhteevah/QBO-FOSS-alternative.git
cd QBO-FOSS-alternative

# Copy and configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, POSTGRES_PASSWORD, ANTHROPIC_API_KEY

# Run production installer
chmod +x install.sh
./install.sh
```

Windows:
```powershell
git clone https://github.com/suhteevah/QBO-FOSS-alternative.git
cd QBO-FOSS-alternative
copy .env.example .env
# Edit .env
.\install.ps1
```

### What runs:
| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL 16 | 5432 | Database |
| FastAPI | 8000 | Backend API |
| React (nginx) | 3000 | Frontend UI |

### Required `.env` for Docker:
```env
SECRET_KEY=your-random-secret-key-here
POSTGRES_PASSWORD=your-strong-password
ANTHROPIC_API_KEY=sk-ant-...   # optional, for AI features
DEBUG=false
```

---

## Method 2: Dev / SQLite (Zero-Config)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Steps
```bash
git clone https://github.com/suhteevah/QBO-FOSS-alternative.git
cd QBO-FOSS-alternative

# Run dev installer
chmod +x install-dev.sh
./install-dev.sh

# Start the app
chmod +x start.sh
./start.sh
```

Windows:
```powershell
git clone https://github.com/suhteevah/QBO-FOSS-alternative.git
cd QBO-FOSS-alternative
.\install-dev.ps1
.\start.ps1
```

### What happens:
1. Creates Python venv, installs dependencies
2. Installs Node.js packages, builds frontend
3. Creates `openledger.db` SQLite database automatically
4. Seeds demo chart of accounts (26 GAAP-standard accounts)
5. Starts backend on port 8000, frontend on port 3000

### Dev `.env` (auto-configured):
```env
SECRET_KEY=dev-secret-change-in-production
DEBUG=true
# No POSTGRES_PASSWORD needed — uses SQLite
# No ANTHROPIC_API_KEY needed — AI features just won't work
```

---

## After Installation

### Access the App
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs (debug mode only)
- **Health Check:** http://localhost:8000/health

### First Steps
1. Register a new user at `/register`
2. Login at `/login`
3. View the pre-seeded chart of accounts at `/accounts`
4. Create journal entries at `/journal`
5. Import bank transactions at `/transactions`
6. Generate reports at `/reports`

### Demo Data
In SQLite mode, the app auto-seeds:
- 1 demo organization ("Demo Company")
- 26 GAAP-standard accounts (Cash, A/R, A/P, Revenue, Expenses, etc.)

---

## Troubleshooting

### "SECRET_KEY is still set to the default value"
Set a strong `SECRET_KEY` in `.env` before running in production (non-debug) mode.

### Docker: "port already in use"
Change ports in `.env`:
```env
DB_PORT=5433     # default: 5432
```
Or stop conflicting services.

### SQLite: "database is locked"
Only one process should write to SQLite at a time. For concurrent access, use PostgreSQL (Docker mode).

### Python version too old
OpenLedger requires Python 3.11+. Check with:
```bash
python3 --version
```

### Node.js version too old
OpenLedger requires Node.js 18+. Check with:
```bash
node --version
```

---

## All Scripts Reference

| Script | Platform | Purpose |
|--------|----------|---------|
| `bootstrap.sh` | Linux/macOS | One-shot: detect env → install Docker if needed → clone → install → start |
| `bootstrap.ps1` | Windows | One-shot: detect env → install Docker if needed → clone → install → start |
| `install.sh` | Linux/macOS | Docker production setup |
| `install.ps1` | Windows | Docker production setup |
| `install-dev.sh` | Linux/macOS | Dev/SQLite: venv + npm install |
| `install-dev.ps1` | Windows | Dev/SQLite: venv + npm install |
| `start.sh` | Linux/macOS | Start backend (uvicorn) + frontend (vite/nginx) |
| `start.ps1` | Windows | Start backend (uvicorn) + frontend (vite/nginx) |
