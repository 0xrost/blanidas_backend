import json
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Query

from src.auth.schemas import Role
from src.database import DatabaseSession
from src.auth.dependencies import allowed
from src.decorators import domain_errors
from src.failure_type.errors import errors_map
from src.failure_type.models import FailureTypeInfo, FailureTypeCreate, FailureTypeUpdate
from src.failure_type.services import FailureTypeServices
from src.pagination import Pagination, PaginationResponse
from src.sorting import Sorting

router = APIRouter(prefix="/failure-types", tags=["Failure Type"])
services = FailureTypeServices()

@router.get("/", response_model=PaginationResponse[FailureTypeInfo])
async def get_failure_type_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin, Role.engineer]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[FailureTypeInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
    )

@router.post("/", response_model=FailureTypeInfo)
@domain_errors(errors_map)
async def create_failure_type_endpoint(model: FailureTypeCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> FailureTypeInfo:
    return await services.create(data=model.model_dump(exclude_none=True), database=database)

@router.put("/", response_model=FailureTypeInfo)
@domain_errors(errors_map)
async def update_failure_type_endpoint(model: FailureTypeUpdate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> FailureTypeInfo:
    return await services.update(id_=model.id, data=model.model_dump(exclude_none=True), database=database)

@router.delete("/{id_}", response_model=int)
@domain_errors(errors_map)
async def delete_failure_type_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> int:
    return await services.delete(id_=id_, database=database)
