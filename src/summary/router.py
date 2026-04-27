from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends

from src.auth.schemas import Role
from src.database import DatabaseSession
from src.auth.dependencies import allowed
from src.summary.models import SummaryResponse
from src.summary.services import SummaryServices


router = APIRouter(prefix="/summary", tags=["Summary"])

@router.get("/{schema}", response_model=SummaryResponse)
async def get_summary_endpoint(schema: str, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))]) -> SummaryResponse:
    return (await SummaryServices.get(database=database, schema=schema)).model_dump()


