from datetime import datetime
from typing import Callable

from sqlalchemy import select, and_, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.auth.schemas import User
from src.decorators import integrity_errors
from src.equipment.schemas import Equipment
from src.equipment_category.schemas import EquipmentCategory
from src.exceptions import DomainError, DomainErrorCode
from src.failure_type.schemas import FailureType, FailureTypeRepairRequest
from src.filters import FilterRelatedField, apply_filters_wrapper
from src.repair_request.filters import apply_repair_request_filters
from src.repair_request.models import RepairRequestUpdate
from src.repair_request.schemas import RepairRequest, RepairRequestStatus, File, RepairRequestStatusRecord, \
    UsedSparePart, RepairRequestEntry, Urgency
from src.repair_request.sorting import apply_repair_request_sorting
from src.repository import CRUDRepository
from src.sorting import SortingRelatedField, apply_sorting_wrapper
from src.spare_part.schemas import Location
from src.utils import build_relation


filter_related_fields_map = {
    "id": FilterRelatedField(column=RepairRequest.id),
    "status": FilterRelatedField(column=RepairRequest.last_status),
    "equipment_id": FilterRelatedField(column=RepairRequest.equipment_id),
    "urgency": FilterRelatedField(column=RepairRequest.urgency),

    "equipment_category_id": None,
    "equipment_institution_id": None,
    "equipment_serial_number_or_equipment_equipment_model_name": None,
}

class RepairRequestRepository(CRUDRepository[RepairRequest]):
    def __init__(self):
        super().__init__(
            RepairRequest,
            filter_callback=apply_filters_wrapper(apply_repair_request_filters, filter_related_fields_map),
            sorting_callback=apply_sorting_wrapper(apply_repair_request_sorting, {}),
       )

    @integrity_errors()
    async def create(
            self,
            data: dict,
            database: AsyncSession,
            preloads: list[str] | None = None,
            validate_photos_callback: Callable[[], list[str]] | None = None,
    ) -> RepairRequest:
        stmt = (select(RepairRequest)
            .where(
                RepairRequest.equipment_id == data["equipment_id"],
                RepairRequest.last_status != RepairRequestStatus.finished.value
            )
            .order_by(RepairRequest.created_at.desc())
            .limit(1)
        )

        repair_request = (await database.execute(stmt)).scalar()
        if repair_request:
            entry = RepairRequestEntry(
                repair_request_id=repair_request.id,
                created_at=func.now(),
                issue=data["issue"],
            )

            status_record = RepairRequestStatusRecord(
                repair_request_id=repair_request.id,
                assigned_engineer_id=None,
                created_at=func.now(),
                status=RepairRequestStatus.waiting_engineer,
                was_merged=True,
            )
            repair_request.last_status = RepairRequestStatus.waiting_engineer
            repair_request.updated_at = func.now()

            if data["urgency"] == Urgency.critical:
                repair_request.urgency = Urgency.critical
        else:
            repair_request = RepairRequest(
                urgency=data["urgency"],
                equipment_id=data["equipment_id"],
                created_at=func.now(),
                manager_note="",
                engineer_note="",
                last_status=RepairRequestStatus.not_taken
            )
            database.add(repair_request)
            await database.flush()

            entry = RepairRequestEntry(
                repair_request_id=repair_request.id,
                created_at=func.now(),
                issue=data["issue"],
            )

            status_record = RepairRequestStatusRecord(
                repair_request_id=repair_request.id,
                status=RepairRequestStatus.not_taken,
                was_merged=False,
                created_at=func.now(),
                assigned_engineer_id=None,
            )

        database.add(entry)
        database.add(status_record)

        if validate_photos_callback:
            new_filenames = validate_photos_callback()
            if new_filenames:
                await database.flush()

            for new_filename in new_filenames:
                file = File(file_path=new_filename, repair_request_entry_id=entry.id)
                database.add(file)

        await database.commit()
        database.expunge_all()

        options = build_relation(RepairRequest, preloads)
        stmt = (select(RepairRequest).options(*options).where(RepairRequest.id == repair_request.id))
        result = await database.execute(stmt)
        return result.scalars().first()

    @integrity_errors()
    async def update(self, id_: int, data: dict, database: AsyncSession, preloads: list[str] | None = None) -> RepairRequest:
        data_model = RepairRequestUpdate.model_validate(data)

        fields_to_update = data_model.model_dump(exclude={"status_history", "used_spare_parts", "failure_types_ids"}, exclude_unset=True)
        result = await database.execute(
            update(RepairRequest)
            .where(RepairRequest.id == id_)
            .values(fields_to_update)
            .returning(RepairRequest.id)
        )

        if result.first() is None:
            raise DomainError(code=DomainErrorCode.not_entity)

        if data_model.failure_types_ids:
            await database.execute(delete(FailureTypeRepairRequest).where(FailureTypeRepairRequest.repair_request_id == id_))
            for failure_type_id in data_model.failure_types_ids:
                await database.execute(insert(FailureTypeRepairRequest).values(
                    repair_request_id=id_,
                    failure_type_id=failure_type_id,
                ))

        if data_model.status_history:
            await database.execute(insert(RepairRequestStatusRecord).values(
                repair_request_id=id_,
                created_at=func.now(),
                assigned_engineer_id=data_model.status_history.assigned_engineer_id,
                status=data_model.status_history.status,
            ))
            completed_at = func.now() if data_model.status_history.status == RepairRequestStatus.finished else None
            await database.execute(update(RepairRequest).where(RepairRequest.id == id_).values(
                last_status=data_model.status_history.status,
                completed_at=completed_at
            ))

        if data_model.used_spare_parts is not None:
            used_spare_parts = (await database.execute(select(UsedSparePart).where(UsedSparePart.repair_request_id == id_))).scalars().all()
            old_parts = {(usp.spare_part_id, usp.institution_id): usp for usp in used_spare_parts}
            new_parts = {(usp.spare_part_id, usp.institution_id): usp for usp in data_model.used_spare_parts}

            for key, old_usp in old_parts.items():
                spare_part_id, institution_id = key
                old_restored_qty = old_usp.restored_quantity
                new_qty = new_parts.get(key, None).new_quantity if key in new_parts else 0
                new_restored_qty = new_parts.get(key, None).restored_quantity if key in new_parts else 0

                diff_new_qty = old_usp.new_quantity - new_qty
                diff_restored_qty = old_restored_qty - new_restored_qty

                if diff_new_qty > 0 or diff_restored_qty > 0:
                    stmt = insert(Location).values(
                        spare_part_id=spare_part_id,
                        institution_id=institution_id,
                        new_quantity=diff_new_qty,
                        restored_quantity=diff_restored_qty,
                    ).on_conflict_do_update(
                        index_elements=[
                            Location.spare_part_id,
                            Location.institution_id,
                        ],
                        set_={
                            "new_quantity": Location.new_quantity + diff_new_qty,
                            "restored_quantity": Location.restored_quantity + diff_restored_qty,
                        }
                    )
                    await database.execute(stmt)


            for key, new_usp in new_parts.items():
                spare_part_id, institution_id = key
                old_new_qty = old_parts.get(key).new_quantity if key in old_parts else 0
                old_restored_qty = old_parts.get(key).restored_quantity if key in old_parts else 0

                diff_qty = new_usp.new_quantity - old_new_qty
                diff_restored_qty = new_usp.restored_quantity - old_restored_qty

                if diff_qty > 0 or diff_restored_qty > 0:
                    stmt = insert(Location).values(
                        spare_part_id=spare_part_id,
                        institution_id=institution_id,
                        new_quantity=diff_qty,
                        restored_quantity=diff_restored_qty,
                    ).on_conflict_do_update(
                        index_elements=[
                            Location.spare_part_id,
                            Location.institution_id,
                        ],
                        set_={
                            "new_quantity": Location.new_quantity - diff_qty,
                            "restored_quantity": Location.restored_quantity - diff_restored_qty,
                        }
                    ).returning(Location.id, Location.new_quantity, Location.restored_quantity)
                    row = (await database.execute(stmt)).first()
                    if row is not None and row.new_quantity == 0 and row.restored_quantity == 0:
                        await database.execute(delete(Location).where(Location.id == row.id))

            await database.execute(delete(UsedSparePart).where(UsedSparePart.repair_request_id == id_))
            for usp in data_model.used_spare_parts:
                await database.execute(insert(UsedSparePart).values(
                    repair_request_id=id_,
                    spare_part_id=usp.spare_part_id,
                    institution_id=usp.institution_id,
                    new_quantity=usp.new_quantity,
                    restored_quantity=usp.restored_quantity,
                    note=usp.note,
                ))

        await database.commit()

        options = build_relation(RepairRequest, preloads)
        stmt = select(RepairRequest).options(*options).where(RepairRequest.id == id_)
        result = await database.execute(stmt)
        return result.scalars().first()

class FileRepository(CRUDRepository[File]):
    def __init__(self):
        super().__init__(File)

    async def get_by_repair_request_id(self, repair_request_id: int, database: AsyncSession) -> list[File]:
        stmt = select(File).where(File.repair_request_id == repair_request_id)
        return list((await database.execute(stmt)).unique().scalars().all())