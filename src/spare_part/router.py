import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks
from fastapi.params import Depends, Query

from src.auth.schemas import Role
from src.decorators import domain_errors
from src.sorting import Sorting
from src.database import DatabaseSession
from src.pagination import Pagination
from src.auth.dependencies import allowed
from src.pagination import PaginationResponse
from src.mailer.dependencies import MailerServiceDep
from src.spare_part.errors import errors_map
from src.spare_part.models import SparePartInfo, SparePartCreate, SparePartUpdate
from src.spare_part.services import SparePartServices

router = APIRouter(prefix="/spare-parts", tags=["Spare Parts"])
services = SparePartServices()

@router.get("/", response_model=PaginationResponse[SparePartInfo])
async def get_spare_part_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[SparePartInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
        preloads=[
            "compatible_models",
            "locations",
            "locations.institution",
            "spare_part_category",
        ]
    )

@router.post("/", response_model=SparePartInfo)
@domain_errors(errors_map)
async def create_spare_part_endpoint(model: SparePartCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))]) -> SparePartInfo:
    return await services.create(
        data=model.model_dump(exclude_none=True),
        database=database,
        preloads=[
            "compatible_models",
            "locations",
            "locations.institution",
            "spare_part_category",
        ]
    )

@router.put("/", response_model=SparePartInfo)
@domain_errors(errors_map)
async def update_spare_part_endpoint(
        model: SparePartUpdate,
        database: DatabaseSession,
        mailer: MailerServiceDep,
        background_task: BackgroundTasks,
        _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))]
) -> SparePartInfo:
    return await services.update(
        id_=model.id,
        data=model.model_dump(exclude_none=True),
        database=database,
        mailer=mailer,
        background_tasks=background_task,
        preloads=[
            "compatible_models",
            "spare_part_category",
            "locations",
            "locations.institution",
        ]
    )

@router.delete("/{id_}", response_model=int)
@domain_errors(errors_map)
async def delete_spare_part_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))]) -> int:
    return await services.delete(id_=id_, database=database)
