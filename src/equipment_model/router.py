import json
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Query

from src.auth.schemas import Role
from src.database import DatabaseSession
from src.decorators import domain_errors
from src.auth.dependencies import allowed
from src.equipment_model.errors import errors_map
from src.equipment_model.models import EquipmentModelInfo, EquipmentModelCreate, EquipmentModelUpdate
from src.equipment_model.services import EquipmentModelServices
from src.pagination import PaginationResponse, Pagination
from src.sorting import Sorting

router = APIRouter(prefix="/equipment-models", tags=["Equipment Model"])
services = EquipmentModelServices()

@router.get("/", response_model=PaginationResponse[EquipmentModelInfo])
async def get_equipment_model_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[EquipmentModelInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
    )

@router.post("/", response_model=EquipmentModelInfo)
@domain_errors(errors_map)
async def create_equipment_model_endpoint(model: EquipmentModelCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> EquipmentModelInfo:
    return await services.create(data=model.model_dump(exclude_none=True), database=database)

@router.put("/", response_model=EquipmentModelInfo)
@domain_errors(errors_map)
async def update_equipment_model_endpoint(model: EquipmentModelUpdate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> EquipmentModelInfo:
    return await services.update(id_=model.id, data=model.model_dump(exclude_none=True), database=database)

@router.delete("/{id_}", response_model=int)
@domain_errors(errors_map)
async def delete_equipment_model_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> int:
    return await services.delete(id_=id_, database=database)