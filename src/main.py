from contextlib import asynccontextmanager

from fastapi import FastAPI
from datetime import date, datetime

from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware

from src.auth.services import AuthServices
from src.config import get_settings
from src.database import session_factory
import src.auth.models as auth_models
import src.auth.schemas as auth_schemas

from src.mailer.subscriber import on_low_stock, on_repair_request_created # need
from src.middlewares import error_handler, validation_exception_handler

from src.router import router

@asynccontextmanager
async def lifespan(_: FastAPI):
    async with session_factory() as session:
        settings = get_settings()
        superuser = auth_models.UserCreate.model_construct(
            username="",
            phone_number="+380680000000",
            department="",
            workplace_id=None,
            hire_at=datetime.now(),
            email=settings.superuser_email,
            password=settings.superuser_password,
            role=auth_schemas.Role.admin,
            receive_low_stock_notification=True,
            receive_repair_request_created_notification=True
        )
        auth_service = AuthServices()
        await auth_service.create_if_not_exists(data=superuser.model_dump(exclude_none=True), database=session)
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(router)

app.middleware("http")(error_handler)
app.exception_handler(RequestValidationError)(validation_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.0.106:5173"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    allow_methods=["*"],
)