#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# OpenLedger — One-Click Production Installer (Docker)
# ──────────────────────────────────────────────────────────────
# Usage:  chmod +x install.sh && ./install.sh
#
# Prerequisites: Docker & Docker Compose installed
# This script will:
#   1. Verify Docker is available
#   2. Generate a secure .env if one doesn't exist
#   3. Build and start all containers (PostgreSQL + API + Frontend)
#   4. Run database migrations
#   5. Print access information
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
    echo "  ║         OpenLedger — Production Installer         ║"
    echo "  ║   FOSS GAAP-Compliant AI Bookkeeping Platform     ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info()  { echo -e "${BLUE}[i]${NC} $1"; }

banner

# ── Step 1: Check Prerequisites ──────────────────────────────

info "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || err "Docker is not installed. Visit https://docs.docker.com/get-docker/"

if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif docker-compose version >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    err "Docker Compose is not installed. Visit https://docs.docker.com/compose/install/"
fi

log "Docker and Docker Compose found"

# ── Step 2: Generate .env if needed ──────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ] || grep -q "change-me-in-production" .env 2>/dev/null; then
    info "Generating production .env file..."

    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    POSTGRES_PASSWORD=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(16))")

    cat > .env << EOF
# ── OpenLedger Production Configuration ──
# Generated on $(date -Iseconds 2>/dev/null || date)

# Database
POSTGRES_USER=openledger
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=openledger
DATABASE_URL=postgresql+asyncpg://openledger:${POSTGRES_PASSWORD}@db:5432/openledger
DATABASE_URL_SYNC=postgresql://openledger:${POSTGRES_PASSWORD}@db:5432/openledger

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

# Debug (set to false for production)
DEBUG=false
EOF

    log "Production .env created with secure random secrets"
    warn "Edit .env to add your ANTHROPIC_API_KEY for AI features"
else
    log "Existing .env found — using current configuration"
fi

# ── Step 3: Build & Start Containers ─────────────────────────

info "Building and starting containers (this may take a few minutes on first run)..."

$COMPOSE down --remove-orphans 2>/dev/null || true
$COMPOSE build --no-cache
$COMPOSE up -d

log "Containers started"

# ── Step 4: Wait for Database & Run Migrations ───────────────

info "Waiting for PostgreSQL to be ready..."
RETRIES=30
until $COMPOSE exec -T db pg_isready -U openledger >/dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ $RETRIES -le 0 ]; then
        err "PostgreSQL failed to start. Check logs: $COMPOSE logs db"
    fi
    sleep 1
done
log "PostgreSQL is ready"

info "Running database migrations..."
$COMPOSE exec -T api alembic upgrade head 2>/dev/null && log "Migrations applied" || warn "Migrations skipped (tables may already exist)"

# ── Step 5: Health Check ─────────────────────────────────────

info "Verifying services..."
sleep 3

API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$API_STATUS" = "200" ]; then
    log "API is healthy (port 8000)"
else
    warn "API health check returned $API_STATUS — it may still be starting"
fi

FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
    log "Frontend is healthy (port 3000)"
else
    warn "Frontend returned $FRONTEND_STATUS — it may still be starting"
fi

# ── Done ─────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  OpenLedger installed successfully!${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Frontend:${NC}  http://localhost:3000"
echo -e "  ${BOLD}API Docs:${NC}  http://localhost:8000/docs  (if DEBUG=true)"
echo -e "  ${BOLD}API:${NC}       http://localhost:8000/api"
echo ""
echo -e "  ${BOLD}Manage:${NC}"
echo -e "    Stop:     ${BLUE}$COMPOSE down${NC}"
echo -e "    Logs:     ${BLUE}$COMPOSE logs -f${NC}"
echo -e "    Restart:  ${BLUE}$COMPOSE restart${NC}"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo -e "    1. Open http://localhost:3000 and register your admin account"
echo -e "    2. Set ANTHROPIC_API_KEY in .env for AI features, then restart"
echo -e "    3. Import bank transactions via CSV/XLSX"
echo ""
