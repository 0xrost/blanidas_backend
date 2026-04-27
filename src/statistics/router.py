from datetime import date, datetime
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

from src.auth.dependencies import allowed
from src.auth.schemas import Role
from src.database import DatabaseSession
from src.statistics.models import StatisticsTimeStep, TimeFrame, StatisticsResponse, StatisticsFilters
from src.statistics.services import StatisticsServices

router = APIRouter(prefix="/statistics", tags=["Statistics"])

def get_time_frame(
        from_date: Optional[datetime] = Query(None),
        to_date: Optional[datetime] = Query(None),
        step: StatisticsTimeStep = Query(default=StatisticsTimeStep.month),
) -> TimeFrame:
    return TimeFrame(
        from_date=from_date or date.min,
        to_date=to_date or date.max,
        step=step,
    )

def get_filters(
        time_frame: Annotated[TimeFrame, Depends(get_time_frame)],
        institution_ids: Optional[List[int]] = Query(None),
        equipment_model_ids: Optional[List[int]] = Query(None),
        failure_type_ids: Optional[List[int]] = Query(None),
) -> StatisticsFilters:
    return StatisticsFilters(
        institution_ids=institution_ids or [],
        equipment_model_ids=equipment_model_ids or [],
        failure_type_ids=failure_type_ids or [],
        time_frame=time_frame,
    )

@router.get("/", response_model=StatisticsResponse)
async def get_statistics_endpoint(
        database: DatabaseSession,
        filters: Annotated[StatisticsFilters, Depends(get_filters)],
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]
) -> StatisticsResponse:
    return await StatisticsServices.get_dashboard(database=database, data=filters)

@router.get("/export-excel")
async def export_statistics_excel(
        database: DatabaseSession,
        filters: Annotated[StatisticsFilters, Depends(get_filters)],
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]
) -> StreamingResponse:
    return await StatisticsServices.export_statistics_excel(database=database, filters=filters)
