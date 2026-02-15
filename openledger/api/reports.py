"""Financial Reports API — stub, will be fully built out."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_report_types():
    return {
        "available_reports": [
            "profit_loss",
            "balance_sheet",
            "trial_balance",
            "cash_flow",
        ]
    }
