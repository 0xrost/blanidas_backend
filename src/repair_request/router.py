import json
from typing import Annotated

from fastapi import APIRouter, UploadFile, BackgroundTasks, Query
from fastapi.params import Depends, Form, File

from src.auth.schemas import Role
from src.decorators import domain_errors
from src.repair_request.errors import error_map
from src.repair_request.schemas import Urgency
from src.sorting import SortOrder, Sorting
from src.mailer.dependencies import MailerServiceDep
from src.pagination import PaginationResponse, Pagination
from src.repair_request.models import RepairRequestInfo, RepairRequestCreate, RepairRequestUpdate
from src.database import DatabaseSession
from src.auth.dependencies import allowed
from src.repair_request.services import RepairRequestServices

from src.config import get_settings

router = APIRouter(prefix="/repair-requests", tags=["Repair requests"])

settings = get_settings()
services = RepairRequestServices(
    proxy_url_to_static_files_dir=settings.proxy_url_to_static_files_dir,
    static_files_dir=settings.static_files_dir,
)

@router.get("/", response_model=PaginationResponse[RepairRequestInfo])
async def get_repair_request_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[RepairRequestInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
        preloads=[
            "equipment",
            "equipment.institution",
            "equipment.equipment_model",
            "equipment.equipment_category",
            "failure_types",
            "used_spare_parts",
            "used_spare_parts.institution",
            "used_spare_parts.spare_part",
            "photos",
            "status_history",
            "status_history.assigned_engineer",
        ],
    )

@router.get("/{id_}", response_model=RepairRequestInfo)
async def get_repair_request_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))]) -> RepairRequestInfo:
    return await services.get(
        id_=id_,
        database=database,
        preloads=[
            "equipment",
            "equipment.institution",
            "equipment.equipment_model",
            "equipment.equipment_category",
            "failure_types",
            "used_spare_parts",
            "used_spare_parts.institution",
            "used_spare_parts.spare_part",
            "photos",
            "status_history",
            "status_history.assigned_engineer",
        ]
    )

@router.post("/", response_model=RepairRequestInfo)
@domain_errors(error_map)
async def create_repair_request_endpoint(
        database: DatabaseSession,
        background_tasks: BackgroundTasks,
        mailer: MailerServiceDep,
        issue: str = Form(...),
        urgency: Urgency = Form(...),
        equipment_id: int = Form(...),
        photos: list[UploadFile] | None = File(None),
) -> RepairRequestInfo:
    photos = photos or []

    model = RepairRequestCreate(
        issue=issue,
        urgency=urgency,
        equipment_id=equipment_id,
    )

    return await services.create(
        data=model.model_dump(exclude_none=True),
        database=database,
        background_tasks=background_tasks,
        mailer=mailer,
        photos=photos,
        preloads=[
            "equipment.institution",
            "equipment.equipment_model",
            "failure_types",
            "used_spare_parts",
            "photos",
            "status_history",
            "status_history.assigned_engineer",
        ]
    )


@router.put("/", response_model=RepairRequestInfo)
@domain_errors(error_map)
async def update_repair_request_endpoint(
        model: RepairRequestUpdate,
        database: DatabaseSession,
        mailer: MailerServiceDep,
        background_task: BackgroundTasks,
        _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))]
) -> RepairRequestInfo:
    return await services.update(
        id_=model.id,
        database=database,
        data=model.model_dump(exclude_none=True),
        mailer=mailer,
        background_tasks=background_task,
        preloads=[
            "failure_types",
            "used_spare_parts",
            "used_spare_parts.institution",
            "used_spare_parts.spare_part",
            "photos",
            "status_history",
            "status_history.assigned_engineer",
            "equipment",
            "equipment.institution",
        ]
    )

@router.delete("/{id_}", response_model=int)
@domain_errors(error_map)
async def delete_repair_request_endpoint(
        id_: int,
        database: DatabaseSession,
        background_tasks: BackgroundTasks,
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]
) -> int:
    return await services.delete(id_=id_, database=database, background_tasks=background_tasks)

