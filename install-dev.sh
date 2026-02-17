#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# OpenLedger — Lightweight Dev/Demo Installer (No Docker)
# ──────────────────────────────────────────────────────────────
# Usage:  chmod +x install-dev.sh && ./install-dev.sh
#
# Prerequisites: Python 3.11+ and Node.js 18+
# Uses SQLite (no PostgreSQL needed) — perfect for demos & dev
# ──────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${BLUE}${BOLD}"
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║      OpenLedger — Dev / Demo Installer            ║"
    echo "  ║   No Docker • SQLite • Zero External Deps         ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info()  { echo -e "${BLUE}[i]${NC} $1"; }

banner

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Step 1: Check Prerequisites ──────────────────────────────

info "Checking prerequisites..."

# Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PY_VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        PY_MAJOR=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        PY_MINOR=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done
[ -z "$PYTHON" ] && err "Python 3.11+ is required. Found: $(python3 --version 2>/dev/null || echo 'none')"
log "Python $PY_VER found ($PYTHON)"

# Node.js
command -v node >/dev/null 2>&1 || err "Node.js 18+ is required. Visit https://nodejs.org/"
NODE_VER=$(node -v | sed 's/v//' | cut -d. -f1)
[ "$NODE_VER" -ge 18 ] || err "Node.js 18+ required. Found: $(node -v)"
log "Node.js $(node -v) found"

# npm
command -v npm >/dev/null 2>&1 || err "npm not found"
log "npm $(npm -v) found"

# ── Step 2: Python Virtual Environment ───────────────────────

if [ ! -d "venv" ]; then
    info "Creating Python virtual environment..."
    $PYTHON -m venv venv
    log "Virtual environment created"
else
    log "Virtual environment already exists"
fi

# Activate
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

info "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
log "Python dependencies installed"

# ── Step 3: Configure Environment ────────────────────────────

if [ ! -f .env ] || grep -q "postgresql" .env 2>/dev/null; then
    info "Creating SQLite development .env..."

    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)

    cat > .env << EOF
# ── OpenLedger Dev/Demo Configuration ──
# Generated on $(date -Iseconds 2>/dev/null || date)
# Using SQLite — no PostgreSQL needed

# Database (SQLite for dev/demo)
DATABASE_URL=sqlite+aiosqlite:///./openledger.db
DATABASE_URL_SYNC=sqlite:///./openledger.db

# Security
SECRET_KEY=${SECRET_KEY}

# AI (optional — leave empty to disable AI features)
ANTHROPIC_API_KEY=
SONNET_MODEL=claude-sonnet-4-20250514

# OCR
OCR_ENGINE=tesseract

# Accounting
ACCOUNTING_BASIS=accrual
DEFAULT_FISCAL_YEAR_START=1

# Debug mode (enables /docs, CORS *, verbose logging)
DEBUG=true
EOF

    log "SQLite .env created"
else
    log "Existing .env found"
fi

# ── Step 4: Install Frontend Dependencies ────────────────────

info "Installing frontend dependencies..."
cd frontend
npm install --silent 2>/dev/null || npm install
cd "$SCRIPT_DIR"
log "Frontend dependencies installed"

# ── Step 5: Build Frontend for Production Serving ────────────

info "Building frontend..."
cd frontend
npm run build 2>/dev/null
cd "$SCRIPT_DIR"
log "Frontend built successfully"

# ── Done ─────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  OpenLedger installed successfully!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}To start the app:${NC}"
echo ""
echo -e "    ${BLUE}# Terminal 1 — Backend API${NC}"
echo -e "    source venv/bin/activate"
echo -e "    uvicorn openledger.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo -e "    ${BLUE}# Terminal 2 — Frontend Dev Server${NC}"
echo -e "    cd frontend && npm run dev"
echo ""
echo -e "  ${BOLD}Or use the quick-start command:${NC}"
echo -e "    ${BLUE}./start.sh${NC}"
echo ""
echo -e "  ${BOLD}Access:${NC}"
echo -e "    Frontend:  http://localhost:3000"
echo -e "    API Docs:  http://localhost:8000/docs"
echo ""
echo -e "  ${YELLOW}The database (SQLite) auto-creates on first run${NC}"
echo -e "  ${YELLOW}with a full GAAP chart of accounts.${NC}"
echo ""
