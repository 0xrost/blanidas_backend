from datetime import date

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enum import Enum

from src.database import BaseDatabaseModel
from src.institution.schemas import Institution
from src.repair_request.schemas import RepairRequestStatusRecord


class Role(str, Enum):
    engineer = "engineer"
    manager = "manager"
    admin = "admin"

class User(BaseDatabaseModel):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column()
    password_hash: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column(unique=True, index=True)
    phone_number: Mapped[str] = mapped_column()
    role: Mapped[Role] = mapped_column()

    workplace_id: Mapped[int | None] = mapped_column(ForeignKey("institution.id", ondelete="SET NULL"), nullable=True)
    workplace: Mapped["Institution | None"] = relationship(back_populates="users", lazy="noload")

    department: Mapped[str] = mapped_column()
    hire_at: Mapped[date] = mapped_column(DateTime(timezone=True))

    receive_low_stock_notification: Mapped[bool] = mapped_column()
    receive_repair_request_created_notification: Mapped[bool] = mapped_column()

    status_history: Mapped[list["RepairRequestStatusRecord"]] = relationship(back_populates="assigned_engineer", lazy="noload")

