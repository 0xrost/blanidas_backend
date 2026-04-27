import json
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Query

from src.auth.dependencies import allowed
from src.auth.schemas import Role
from src.decorators import domain_errors
from src.equipment.errors import errors_map
from src.equipment.models import EquipmentInfo, EquipmentCreate, EquipmentUpdate, EquipmentQrData
from src.equipment.services import EquipmentServices
from src.pagination import PaginationResponse, Pagination
from src.database import DatabaseSession
from src.sorting import Sorting

router = APIRouter(prefix="/equipment", tags=["Equipment"])
services = EquipmentServices()

@router.get("/", response_model=PaginationResponse[EquipmentInfo])
async def get_equipment_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[EquipmentInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
        preloads=[
            "equipment_model",
            "equipment_category",
            "manufacturer",
            "institution",
        ]
    )

@router.get("/qr-codes", response_model=list[EquipmentQrData])
@domain_errors(errors_map)
async def get_equipment_qr_data_endpoint(database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> list[EquipmentQrData]:
    return await services.get_qr_data(database=database)

@router.get("/{id_}", response_model=EquipmentInfo)
@domain_errors(errors_map)
async def get_equipment_endpoint(id_: int, database: DatabaseSession) -> EquipmentInfo:
    return await services.get(
        id_=id_,
        database=database,
        preloads = [
            "equipment_model",
            "equipment_category",
            "manufacturer",
            "institution",
        ]
    )

@router.post("/", response_model=EquipmentInfo)
@domain_errors(errors_map)
async def create_equipment_endpoint(model: EquipmentCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> EquipmentInfo:
    return await services.create(
        data=model.model_dump(exclude_none=True),
        database=database,
        preloads=[
            "equipment_model",
            "equipment_category",
            "manufacturer",
            "institution",
        ]
    )

@router.put("/", response_model=EquipmentInfo)
@domain_errors(errors_map)
async def update_equipment_endpoint(model: EquipmentUpdate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> EquipmentInfo:
    return await services.update(
        id_=model.id,
        data=model.model_dump(exclude_none=True),
        database=database,
        preloads=[
            "equipment_model",
            "equipment_category",
            "manufacturer",
            "institution",
        ]
    )

@router.delete("/{id_}", response_model=int)
@domain_errors(errors_map)
async def delete_equipment_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> int:
    return await services.delete(id_=id_, database=database)