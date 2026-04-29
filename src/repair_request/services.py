import uuid
import os
from math import ceil
from typing import Any

import magic

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import AuthRepository
from src.config import get_settings
from src.exceptions import DomainError, DomainErrorCode
from src.sorting import Sorting
from src.auth.schemas import User
from src.event import emit, EventTypes
from src.mailer.smtp import MailerService
from src.mailer.models import RepairRequestCreatedMessagePayload
from src.pagination import Pagination, PaginationResponse
from src.repair_request.models import RepairRequestInfo, RepairRequestUpdate
from src.repair_request.repository import RepairRequestRepository, FileRepository
from src.repair_request.schemas import RepairRequest, File
from src.repository import CRUDRepository
from src.services import GenericServices
from src.spare_part.repository import SparePartRepository
from src.spare_part.services import SparePartServices

ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "gif", "tiff", "tif"}
ALLOWED_PHOTO_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}

settings = get_settings()

def form_url_to_file(static_dir: str, filename: str) -> str:
    return os.path.join(static_dir, filename)

class RepairRequestServices(GenericServices[RepairRequest, RepairRequestInfo]):
    def __init__(self, proxy_url_to_static_files_dir: str, static_files_dir: str):
        super().__init__(RepairRequestRepository(), RepairRequestInfo)
        self.spare_parts_services = SparePartServices()
        self.auth_repo = AuthRepository()
        self.file_repo = FileRepository()

        self.static_files_dir = static_files_dir
        self.proxy_url_to_static_files_dir = proxy_url_to_static_files_dir

    async def paginate(
            self,
            database: AsyncSession,
            pagination: Pagination,
            filters: dict[str, Any] | Any = None,
            sorting: Sorting | None = None,
            preloads: list[str] | None = None,
    ) -> PaginationResponse[RepairRequestInfo]:
        result = await self.repo.fetch(
            database=database,
            limit=pagination.limit,
            offset=pagination.offset,
            filters=filters,
            sorting=sorting,
            preloads=preloads,
        )

        models = [self.return_type.model_validate(x.__dict__, from_attributes=True) for x in result[0]]
        for model in models:
            for photo in model.photos:
                photo.file_path = form_url_to_file(self.proxy_url_to_static_files_dir, photo.file_path)

        total_pages = max(1, ceil(result[1] / pagination.limit))
        return PaginationResponse.model_validate({
            "items": models,
            "total": result[1],
            "page": pagination.page,
            "pages": total_pages,
            "limit": pagination.limit,
            "has_next": pagination.page < total_pages,
            "has_prev": pagination.page > 1,
        })

    async def create(
            self,
            data: dict,
            database: AsyncSession,
            mailer: MailerService | None = None,
            background_tasks: BackgroundTasks | None = None,
            photos: list[UploadFile] | None = None,
            preloads: list[str] | None = None,
    ) -> RepairRequestInfo:
        photos = photos if photos else []

        def validate_photos() -> list[str]:
            new_files = {}
            try:
                for photo in photos:
                    ext = photo.filename.split(".")[-1].lower()
                    content = photo.file.read()
                    real_ext = magic.from_buffer(content, mime=True)
                    if (
                            ext not in ALLOWED_PHOTO_EXTENSIONS
                            or photo.content_type not in ALLOWED_PHOTO_MIME
                            or real_ext not in ALLOWED_PHOTO_MIME
                    ):
                        raise
                    new_files[f"{uuid.uuid4()}.{ext}"] = content
            except Exception:
                raise DomainError(code=DomainErrorCode.unsupported_file_type, field="photos")

            saved_files = []
            try:
                for new_filename, photo_content in new_files.items():
                    path = os.path.join(self.static_files_dir, new_filename)
                    with open(path, "wb") as file:
                        file.write(photo_content)
                        saved_files.append(path)
            except Exception as e:
                background_tasks.add_task(lambda: (os.remove(path) for path in saved_files))
                raise e

            return list(new_files.keys())

        repair_request_obj = await self.repo.create(
            data=data,
            database=database,
            preloads=preloads,
            validate_photos_callback=validate_photos,
        )

        repair_request = RepairRequestInfo.model_validate(repair_request_obj.__dict__, from_attributes=True)
        for photo in repair_request.photos:
            photo.file_path = form_url_to_file(self.proxy_url_to_static_files_dir, photo.file_path)

        if background_tasks and mailer:
            receivers = (await self.auth_repo.fetch(
                database=database,
                filters={"receive_repair_request_created_notification": "true"}
            ))[0]
            for receiver in receivers:
                await emit(
                    event_name=EventTypes.repair_request_created.name,
                    background_tasks=background_tasks,
                    to=receiver.email,
                    mailer=mailer,
                    payload=RepairRequestCreatedMessagePayload(
                        receiver_username=receiver.username,
                        repair_request_issue=repair_request.issue,
                        repair_request_urgency=repair_request.urgency.value,
                        repair_request_photos=[photo.file_path for photo in repair_request.photos],
                        equipment_name=repair_request.equipment.equipment_model.name,
                        institution_name=repair_request.equipment.institution.name,
                        repair_request_url=f"{settings.client_url}repair-requests/{repair_request.id}",
                    )
                )

        return repair_request

    async def update(
            self,
            id_: int,
            data: dict,
            database: AsyncSession,
            background_tasks: BackgroundTasks | None = None,
            mailer: MailerService | None = None,
            unique_fields: list[str] | None = None,
            relationship_fields: list[str] | None = None,
            overwrite_relationships: list[str] | None = None,
            preloads: list[str] | None = None,
    ) -> RepairRequestInfo:
        model = RepairRequestUpdate.model_validate(data)
        repair_request = await self.repo.update(
            id_=id_,
            data=data,
            database=database,
            preloads=preloads,
        )

        if model.used_spare_parts:
            spare_part_ids = [x.spare_part_id for x in model.used_spare_parts]
            await self.spare_parts_services.check_quantity(
                ids=spare_part_ids,
                database=database,
                background_tasks=background_tasks,
                mailer=mailer
            )

        for photo in repair_request.photos:
            photo.file_path = form_url_to_file(self.proxy_url_to_static_files_dir, str(photo.file_path))
        return RepairRequestInfo.model_validate(repair_request, from_attributes=True)


    async def delete(
            self,
            id_: int,
            database: AsyncSession,
            relationship_fields: list[str] | None = None,
            background_tasks: BackgroundTasks | None = None,
    ) -> int:
        photos = await self.file_repo.get_by_repair_request_id(id_, database=database)
        for photo in photos:
            path = form_url_to_file(self.static_files_dir, photo.file_path)
            if background_tasks:
                background_tasks.add_task(os.remove, path)
                continue
            os.remove(path)
        return await self.repo.delete(id_=id_, database=database)

    async def get(self, id_: int, database: AsyncSession, preloads: list[str] | None = None) -> RepairRequestInfo:
        result = await self.repo.get(id_=id_, database=database, preloads=preloads)
        if result is None:
            raise DomainError(code=DomainErrorCode.not_entity)

        for photo in result.photos:
            photo.file_path = form_url_to_file(self.proxy_url_to_static_files_dir, str(photo.file_path))

        return RepairRequestInfo.model_validate(result, from_attributes=True)
