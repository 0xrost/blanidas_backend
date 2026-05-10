from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, DateTime, func, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from src.database import BaseDatabaseModel
from src.failure_type.schemas import FailureType, FailureTypeRepairRequest


class RepairRequestStatus(str, Enum):
    waiting_engineer = "waiting_engineer"
    in_progress = "in_progress"
    not_taken = "not_taken"
    waiting_spare_parts = "waiting_spare_parts"
    finished = "finished"

class Urgency(str, Enum):
    critical = "critical"
    non_critical = "non_critical"

class RepairRequestStatusRecord(BaseDatabaseModel):
    __tablename__ = "repair_request_status_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[RepairRequestStatus] = mapped_column()
    was_merged: Mapped[bool] = mapped_column(default=False)

    assigned_engineer_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    assigned_engineer: Mapped["User"] = relationship(back_populates="status_history", lazy="noload")

    repair_request_id: Mapped[int] = mapped_column(ForeignKey("repair_request.id", ondelete="CASCADE"))
    repair_request: Mapped["RepairRequest"] = relationship(back_populates="status_history", lazy="noload")

class File(BaseDatabaseModel):
    __tablename__ = "file"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(unique=True)

    repair_request_entry_id: Mapped[int] = mapped_column(ForeignKey("repair_request_entry.id", ondelete="CASCADE"))
    repair_request_entry: Mapped["RepairRequestEntry"] = relationship(back_populates="photos", lazy="noload")

class UsedSparePart(BaseDatabaseModel):
    __tablename__ = "used_spare_part"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    new_quantity: Mapped[int] = mapped_column()
    restored_quantity: Mapped[int] = mapped_column(default=0, server_default="0")

    note: Mapped[str] = mapped_column()

    spare_part_id: Mapped[int] = mapped_column(ForeignKey("spare_part.id", ondelete="CASCADE"))
    spare_part: Mapped["SparePart"] = relationship(back_populates="used_spare_parts", lazy="noload")

    institution_id: Mapped[int] = mapped_column(ForeignKey("institution.id", ondelete="CASCADE"))
    institution: Mapped["Institution"] = relationship(back_populates="used_spare_parts", lazy="noload")

    repair_request_id: Mapped[int] = mapped_column(ForeignKey("repair_request.id", ondelete="CASCADE"))
    repair_request: Mapped["RepairRequest"] = relationship(back_populates="used_spare_parts", lazy="noload")

class RepairRequestEntry(BaseDatabaseModel):
    __tablename__ = "repair_request_entry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    issue: Mapped[str] = mapped_column(String(600))
    photos: Mapped[list["File"]] = relationship(
        back_populates="repair_request_entry",
        cascade="all, delete-orphan",
        lazy="noload"
    )

    repair_request_id: Mapped[int] = mapped_column(ForeignKey("repair_request.id", ondelete="CASCADE"))
    repair_request: Mapped["RepairRequest"] = relationship(back_populates="entries", lazy="noload")


class RepairRequest(BaseDatabaseModel):
    __tablename__ = "repair_request"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    urgency: Mapped[Urgency] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[RepairRequestStatus] = mapped_column()

    manager_note: Mapped[str] = mapped_column()
    engineer_note: Mapped[str] = mapped_column()

    entries: Mapped[list["RepairRequestEntry"]] = relationship(
        back_populates="repair_request",
        cascade="all, delete-orphan",
        order_by="asc(RepairRequestEntry.created_at)",
        lazy="noload"
    )

    used_spare_parts: Mapped[list["UsedSparePart"]] = relationship(
        back_populates="repair_request",
        cascade="all, delete-orphan",
        lazy="noload"
    )

    failure_types: Mapped[list["FailureType"]] = relationship(
        back_populates="repair_requests",
        secondary=FailureTypeRepairRequest.__table__,
        lazy="noload"
    )

    status_history: Mapped[list["RepairRequestStatusRecord"]] = relationship(
        back_populates="repair_request",
        cascade="all, delete-orphan",
        order_by="desc(RepairRequestStatusRecord.created_at)",
        lazy="noload"
    )

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True)
    equipment: Mapped["Equipment"] = relationship(back_populates="repair_requests", lazy="noload")
