import json
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from fastapi.temp_pydantic_v1_params import Query

from src.auth.schemas import Role
from src.database import DatabaseSession
from src.decorators import domain_errors
from src.pagination import Pagination
from src.pagination import PaginationResponse
from src.auth.dependencies import allowed
from src.sorting import Sorting
from src.spare_part_category.errors import errors_map
from src.spare_part_category.models import SparePartCategoryInfo, SparePartCategoryCreate, SparePartCategoryUpdate
from src.spare_part_category.services import SparePartCategoryServices

router = APIRouter(prefix="/spare-part-categories", tags=["Spare Part Category"])
services = SparePartCategoryServices()

@router.get("/", response_model=PaginationResponse[SparePartCategoryInfo])
async def get_spare_part_category_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.engineer, Role.manager, Role.admin]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[SparePartCategoryInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
    )

@router.post("/", response_model=SparePartCategoryInfo)
@domain_errors(errors_map)
async def create_spare_part_category_endpoint(model: SparePartCategoryCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> SparePartCategoryInfo:
    return await services.create(data=model.model_dump(exclude_none=True), database=database)

@router.put("/", response_model=SparePartCategoryInfo)
@domain_errors(errors_map)
async def update_spare_part_category_endpoint(model: SparePartCategoryUpdate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> SparePartCategoryInfo:
    return await services.update(id_=model.id, data=model.model_dump(exclude_none=True), database=database)

@router.delete("/{id_}", response_model=int)
@domain_errors(errors_map)
async def delete_spare_part_category_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> int:
    return await services.delete(id_=id_, database=database)
