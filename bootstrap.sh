#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# OpenLedger — One-Shot Bootstrap Installer
# ──────────────────────────────────────────────────────────────
#
# Usage (one-liner):
#   curl -fsSL https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.sh | bash
#
# Or with wget:
#   wget -qO- https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.sh | bash
#
# What it does:
#   1. Detects your environment (Docker available? Python? Node?)
#   2. Installs Docker automatically if not found (Linux/macOS)
#   3. Clones the repo (or updates if already cloned)
#   4. Runs the appropriate installer:
#      - Docker mode (production) if Docker is found/installed
#      - Dev mode (SQLite) if Python + Node are found
#   5. Starts the app and opens it in your browser
#
# Options:
#   OPENLEDGER_MODE=docker   Force Docker install
#   OPENLEDGER_MODE=dev      Force dev/SQLite install
#   OPENLEDGER_DIR=./mydir   Custom install directory
#
# ──────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info()  { echo -e "${BLUE}[i]${NC} $1"; }

echo ""
echo -e "${BLUE}${BOLD}"
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║           OpenLedger — One-Shot Install            ║"
echo "  ║   FOSS GAAP-Compliant AI Bookkeeping Platform      ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

REPO_URL="https://github.com/suhteevah/QBO-FOSS-alternative.git"
INSTALL_DIR="${OPENLEDGER_DIR:-openledger}"
MODE="${OPENLEDGER_MODE:-auto}"

# ── Step 1: Detect Environment ───────────────────────────────

HAS_DOCKER=false
HAS_PYTHON=false
HAS_NODE=false
PYTHON_CMD=""

# Check Docker
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    if docker compose version >/dev/null 2>&1 || docker-compose version >/dev/null 2>&1; then
        HAS_DOCKER=true
    fi
fi

# Check Python 3.11+
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PY_MAJOR=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)
        PY_MINOR=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
            HAS_PYTHON=true
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

# Check Node.js 18+
if command -v node >/dev/null 2>&1; then
    NODE_MAJOR=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        HAS_NODE=true
    fi
fi

info "Environment detected:"
echo -e "    Docker:     $([ "$HAS_DOCKER" = true ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo -e "    Python 3.11+: $([ "$HAS_PYTHON" = true ] && echo -e "${GREEN}✓ ($PYTHON_CMD)${NC}" || echo -e "${RED}✗${NC}")"
echo -e "    Node.js 18+:  $([ "$HAS_NODE" = true ] && echo -e "${GREEN}✓ ($(node -v))${NC}" || echo -e "${RED}✗${NC}")"
echo ""

# ── Step 2: Install Docker if needed ───────────────────────────

install_docker() {
    info "Docker not found — attempting automatic install..."
    echo ""

    OS_TYPE="$(uname -s)"
    case "$OS_TYPE" in
        Linux)
            if [ "$(id -u)" -ne 0 ]; then
                warn "Root privileges required to install Docker."
                info "Re-running Docker install with sudo..."
                if ! command -v sudo >/dev/null 2>&1; then
                    err "sudo is not available. Please install Docker manually:
  https://docs.docker.com/engine/install/"
                fi
                sudo sh -c 'curl -fsSL https://get.docker.com | sh'
            else
                curl -fsSL https://get.docker.com | sh
            fi

            # Start Docker daemon if not running
            if command -v systemctl >/dev/null 2>&1; then
                sudo systemctl start docker 2>/dev/null || true
                sudo systemctl enable docker 2>/dev/null || true
            fi

            # Add current user to docker group so sudo isn't needed
            if [ "$(id -u)" -ne 0 ]; then
                sudo usermod -aG docker "$USER" 2>/dev/null || true
                warn "Added $USER to the docker group. You may need to log out and back in."
            fi
            ;;
        Darwin)
            if command -v brew >/dev/null 2>&1; then
                info "Installing Docker Desktop via Homebrew..."
                brew install --cask docker
                info "Starting Docker Desktop..."
                open -a Docker
                info "Waiting for Docker to start (this may take a minute)..."
                for i in $(seq 1 30); do
                    if docker info >/dev/null 2>&1; then break; fi
                    sleep 2
                done
            else
                err "Please install Docker Desktop manually:
  https://www.docker.com/products/docker-desktop/

Or install Homebrew first:
  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            fi
            ;;
        *)
            err "Unsupported OS ($OS_TYPE). Please install Docker manually:
  https://docs.docker.com/get-docker/"
            ;;
    esac

    # Re-check Docker after install
    if docker info >/dev/null 2>&1; then
        if docker compose version >/dev/null 2>&1 || docker-compose version >/dev/null 2>&1; then
            HAS_DOCKER=true
            log "Docker installed and running!"
        else
            err "Docker installed but Docker Compose is missing. Please install Docker Compose:
  https://docs.docker.com/compose/install/"
        fi
    else
        err "Docker installation completed but Docker daemon is not responding.
Please start Docker and re-run this script."
    fi
}

# ── Step 3: Choose Install Mode ──────────────────────────────

if [ "$MODE" = "auto" ]; then
    if [ "$HAS_DOCKER" = true ]; then
        MODE="docker"
        info "Auto-selected: ${BOLD}Docker (production)${NC} mode"
    elif [ "$HAS_PYTHON" = true ] && [ "$HAS_NODE" = true ]; then
        MODE="dev"
        info "Auto-selected: ${BOLD}Dev/SQLite${NC} mode (no Docker found)"
    else
        echo ""
        info "Neither Docker nor Python+Node found."
        info "Installing Docker for production mode..."
        install_docker
        MODE="docker"
    fi
fi

# If Docker mode requested but Docker missing, install it
if [ "$MODE" = "docker" ] && [ "$HAS_DOCKER" = false ]; then
    install_docker
fi
if [ "$MODE" = "dev" ]; then
    [ "$HAS_PYTHON" = false ] && err "Dev mode requires Python 3.11+"
    [ "$HAS_NODE" = false ] && err "Dev mode requires Node.js 18+"
fi

# ── Step 4: Check for git ────────────────────────────────────

command -v git >/dev/null 2>&1 || err "git is required. Install it: https://git-scm.com/"

# ── Step 5: Clone or Update Repo ─────────────────────────────

if [ -d "$INSTALL_DIR/.git" ]; then
    info "Existing installation found — pulling latest..."
    cd "$INSTALL_DIR"
    git pull --ff-only origin main 2>/dev/null || warn "Could not pull (offline or uncommitted changes)"
else
    info "Cloning OpenLedger into ./${INSTALL_DIR}..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    log "Repository cloned"
fi

# ── Step 6: Run Installer ────────────────────────────────────

if [ "$MODE" = "docker" ]; then
    info "Running Docker production installer..."
    chmod +x install.sh
    ./install.sh
else
    info "Running dev/SQLite installer..."
    chmod +x install-dev.sh start.sh
    ./install-dev.sh

    echo ""
    info "Starting OpenLedger..."
    ./start.sh &
    CHILD=$!

    # Give it a moment to start
    sleep 4

    # Try to open browser
    URL="http://localhost:3000"
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL" 2>/dev/null &
    elif command -v open >/dev/null 2>&1; then
        open "$URL" 2>/dev/null &
    fi

    echo ""
    echo -e "${GREEN}${BOLD}OpenLedger is running at ${URL}${NC}"
    echo -e "Press Ctrl+C to stop."
    echo ""

    wait $CHILD
fi
