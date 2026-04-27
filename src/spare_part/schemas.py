from enum import Enum

from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint, func, select, case, and_
from sqlalchemy.orm import Mapped, relationship, mapped_column, column_property

from src.database import BaseDatabaseModel
from src.institution.schemas import Institution
from src.repair_request.schemas import RepairRequestStatus

class StockStatus(str, Enum):
    in_stock = "in_stock"
    low_stock = "low_stock"
    out_of_stock = "out_of_stock"

class Location(BaseDatabaseModel):
    __tablename__ = "location"
    __table_args__ = (
        UniqueConstraint("institution_id", "spare_part_id"),
        CheckConstraint("quantity >= 0", name="ck_location_quantity_positive"),
        CheckConstraint("restored_quantity <= quantity", name="ck_location_restored_lte_quantity")
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quantity: Mapped[int] = mapped_column()
    restored_quantity: Mapped[int] = mapped_column(default=0, server_default="0")

    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institution.id", ondelete="CASCADE"), nullable=True)
    institution: Mapped["Institution"] = relationship(back_populates="spare_part_locations", lazy="noload")

    spare_part_id: Mapped[int | None] = mapped_column(ForeignKey("spare_part.id", ondelete="CASCADE"))
    spare_part: Mapped["SparePart"] = relationship(back_populates="locations", lazy="noload")


class SparePart(BaseDatabaseModel):
    __tablename__ = "spare_part"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    total_quantity_expr = (
        select(func.coalesce(func.sum(Location.quantity), 0))
        .where(Location.spare_part_id == id)
        .correlate_except(Location)
        .scalar_subquery()
    )

    name: Mapped[str] = mapped_column(unique=True)
    min_quantity: Mapped[int] = mapped_column()
    total_quantity: Mapped[int] = column_property(total_quantity_expr)

    stock_status: Mapped[RepairRequestStatus] = column_property(
        case(
            (
                total_quantity_expr >= min_quantity,
                StockStatus.in_stock,
            ),
            (
                and_(
                    total_quantity_expr < min_quantity,
                    total_quantity_expr > 0,
                ),
                StockStatus.low_stock,
            ),
            else_=StockStatus.out_of_stock,
        )
    )

    spare_part_category_id: Mapped[int | None] = mapped_column(ForeignKey("spare_part_category.id", ondelete="SET NULL"), nullable=True)
    spare_part_category: Mapped["SparePartCategory"] = relationship(back_populates="spare_parts", lazy="noload")

    locations: Mapped[list["Location"]] = relationship(
        back_populates="spare_part",
        lazy="noload",
        order_by="Location.quantity.desc()",
    )

    compatible_models: Mapped[list["EquipmentModel"]] = relationship(
        back_populates="spare_parts",
        secondary="equipment_model_spare_part",
        lazy="noload",
    )

    used_spare_parts: Mapped[list["UsedSparePart"]] = relationship(back_populates="spare_part", lazy="noload")

class EquipmentModelSparePart(BaseDatabaseModel):
    __tablename__ = "equipment_model_spare_part"

    spare_part_id: Mapped[int] = mapped_column(ForeignKey("spare_part.id", ondelete="CASCADE"), primary_key=True)
    equipment_model_id: Mapped[int] = mapped_column(ForeignKey("equipment_model.id", ondelete="CASCADE"), primary_key=True)

