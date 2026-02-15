"""Reconciliation API — stub, will be fully built out."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def reconciliation_status():
    return {"status": "not_implemented"}
