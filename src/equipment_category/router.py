import json
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Query

from src.auth.schemas import Role
from src.auth.dependencies import allowed
from src.decorators import domain_errors
from src.equipment_category.errors import errors_map
from src.equipment_category.models import EquipmentCategoryInfo, EquipmentCategoryCreate, EquipmentCategoryUpdate
from src.equipment_category.services import EquipmentCategoryServices
from src.pagination import PaginationResponse, Pagination
from src.database import DatabaseSession
from src.sorting import Sorting

router = APIRouter(prefix="/equipment-categories", tags=["Equipment Category"])
services = EquipmentCategoryServices()

@router.get("/", response_model=PaginationResponse[EquipmentCategoryInfo])
async def get_equipment_category_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[EquipmentCategoryInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
    )

@router.post("/", response_model=EquipmentCategoryInfo)
@domain_errors(errors_map)
async def create_equipment_category_endpoint(model: EquipmentCategoryCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> EquipmentCategoryInfo:
    return await services.create(data=model.model_dump(exclude_none=True), database=database)

@router.put("/", response_model=EquipmentCategoryInfo)
@domain_errors(errors_map)
async def update_equipment_category_endpoint(model: EquipmentCategoryUpdate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> EquipmentCategoryInfo:
    return await services.update(id_=model.id, data=model.model_dump(exclude_none=True), database=database)

@router.delete("/{id_}", response_model=int)
@domain_errors(errors_map)
async def delete_equipment_category_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> int:
    return await services.delete(id_=id_, database=database)