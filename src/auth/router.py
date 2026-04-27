import json
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends, Query

from src.auth.errors import errors_map
from src.decorators import domain_errors
from src.sorting import Sorting
from src.auth.dependencies import allowed
from src.auth.models import UserCreate, TokenInfo, UserUpdate, UserInfo, TokenRefresh, LoginResponse, Login
from src.auth.schemas import Role
from src.auth.services import AuthServices
from src.database import DatabaseSession
from src.config import SettingsDep
from src.pagination import Pagination, PaginationResponse

router = APIRouter(prefix="/users", tags=["Users"])
auth_services = AuthServices()

@router.get("/", response_model=PaginationResponse[UserInfo])
async def get_users_list_endpoint(
        database: DatabaseSession,
        _: Annotated[None, Depends(allowed(role=[Role.manager, Role.admin]))],
        pagination: Pagination = Depends(),
        sorting: Sorting = Depends(),
        filters: str | None = Query(None),
) -> PaginationResponse[UserInfo]:
    return await auth_services.paginate(
        database=database,
        pagination=pagination,
        filters=json.loads(filters) if filters else None,
        sorting=None if sorting.sort_by == "" else sorting,
        preloads=["workplace"],
    )

@router.post("/", response_model=UserInfo)
@domain_errors(errors_map)
async def create_user_endpoint(model: UserCreate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=Role.admin))]) -> UserInfo:
    return await auth_services.create(data=model.model_dump(exclude_none=True), database=database, preloads=["workplace"])

@router.put("/", response_model=UserInfo)
@domain_errors(errors_map)
async def update_user_endpoint(model: UserUpdate, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=Role.admin))]) -> UserInfo:
    return await auth_services.update(id_=model.id, data=model.model_dump(exclude_none=True), database=database, preloads=["workplace"])

@router.delete("/{id_}", response_model=None)
@domain_errors(errors_map)
async def delete_user_endpoint(id_: int, database: DatabaseSession, _: Annotated[None, Depends(allowed(role=Role.admin))]) -> int:
    return await auth_services.delete(id_=id_, database=database)


@router.post("/login", response_model=LoginResponse)
@domain_errors(errors_map)
async def login(settings: SettingsDep, database: DatabaseSession, model: Login) -> LoginResponse:
    return await auth_services.login(data = model.model_dump(), jwt_settings=settings.jwt, database=database)

@router.post("/refresh", response_model=TokenInfo)
@domain_errors(errors_map)
async def refresh_token_endpoint(model: TokenRefresh, settings: SettingsDep, database: DatabaseSession) -> TokenInfo:
    return await auth_services.refresh_token(data=model.model_dump(), jwt_settings=settings.jwt, database=database)
