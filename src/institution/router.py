import json
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Query

from src.auth.schemas import Role
from src.decorators import domain_errors
from src.institution.errors import errors_map
from src.sorting import Sorting
from src.auth.dependencies import allowed
from src.institution.models import InstitutionInfo, InstitutionCreate, InstitutionUpdate
from src.institution.services import InstitutionServices
from src.pagination import PaginationResponse, Pagination
from src.database import DatabaseSession


router = APIRouter(prefix="/institutions", tags=["Institution"])
services = InstitutionServices()

@router.get("/", response_model=PaginationResponse[InstitutionInfo])
async def get_institution_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin, Role.engineer]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[InstitutionInfo]:
    return await services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
    )

@router.post("/", response_model=InstitutionInfo)
@domain_errors(errors_map)
async def create_institution_endpoint(model: InstitutionCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> InstitutionInfo:
    return await services.create(data=model.model_dump(exclude_none=True), database=database)

@router.put("/", response_model=InstitutionInfo)
@domain_errors(errors_map)
async def update_institution_endpoint(model: InstitutionUpdate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> InstitutionInfo:
    return await services.update(
        id_=model.id,
        data=model.model_dump(exclude_none=True),
        database=database,
    )

@router.delete("/{id_}", response_model=int)
@domain_errors(errors_map)
async def delete_institution_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))]) -> int:
    return await services.delete(id_=id_, database=database)

