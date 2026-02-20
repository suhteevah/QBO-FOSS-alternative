# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for compiling the OpenLedger Python backend into a single
self-contained executable suitable for Tauri sidecar embedding.

Usage:
    pyinstaller desktop/pyinstaller.spec

The resulting binary is then copied by build-sidecar.{ps1,sh} into the
Tauri binaries directory with the correct target-triple suffix.
"""

import os
import sys

# Resolve paths relative to this spec file's location.
SPEC_DIR = os.path.dirname(os.path.abspath(SPECPATH))
PROJECT_ROOT = os.path.normpath(os.path.join(SPEC_DIR, ".."))

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, "openledger", "main.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Alembic configuration and migration scripts
        (os.path.join(PROJECT_ROOT, "alembic.ini"), "."),
        (os.path.join(PROJECT_ROOT, "alembic"), "alembic"),
    ],
    hiddenimports=[
        # ── OpenLedger application modules ──
        "openledger",
        "openledger.main",
        "openledger.config",
        "openledger.database",
        "openledger.models",
        "openledger.schemas",
        "openledger.auth",
        "openledger.ledger",
        "openledger.importer",
        "openledger.report_engine",
        "openledger.reconciliation_engine",
        "openledger.ai_service",
        "openledger.ocr_service",
        "openledger.period_service",
        "openledger.receipt_pipeline",
        "openledger.transaction_pipeline",
        "openledger.cli",
        # ── API routers ──
        "openledger.api",
        "openledger.api.accounts",
        "openledger.api.api_keys",
        "openledger.api.transactions",
        "openledger.api.journal_entries",
        "openledger.api.reports",
        "openledger.api.receipts",
        "openledger.api.ai_query",
        "openledger.api.audit",
        "openledger.api.auth",
        "openledger.api.reconciliation",
        "openledger.api.periods",
        # ── Core dependencies ──
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "pydantic",
        "pydantic_core",
        # ── Database / ORM ──
        "sqlalchemy",
        "sqlalchemy.ext.asyncio",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.postgresql",
        "aiosqlite",
        "asyncpg",
        # ── Alembic migrations ──
        "alembic",
        "alembic.config",
        "alembic.command",
        "alembic.runtime.migration",
        # ── HTTP / networking ──
        "httpx",
        "httpcore",
        "anyio",
        "anyio._backends._asyncio",
        "sniffio",
        # ── Serialisation / utilities ──
        "email_validator",
        "passlib",
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "bcrypt",
        "python_jose",
        "jose",
        "multipart",
        "python_multipart",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "test",
        "unittest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="openledger-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Server needs a console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
