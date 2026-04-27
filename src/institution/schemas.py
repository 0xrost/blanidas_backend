from sqlalchemy.orm import Mapped, relationship, mapped_column
from src.database import BaseDatabaseModel


class Institution(BaseDatabaseModel):
    __tablename__ = "institution"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)
    address: Mapped[str] = mapped_column()
    is_default: Mapped[bool] = mapped_column(default=False)

    contact_email: Mapped[str] = mapped_column()
    contact_phone: Mapped[str] = mapped_column()

    equipment: Mapped[list["Equipment"]] = relationship(back_populates="institution", lazy="noload")
    users: Mapped[list["User"]] = relationship(back_populates="workplace", lazy="noload")

    used_spare_parts: Mapped[list["UsedSparePart"]] = relationship(back_populates="institution", lazy="noload")
    spare_part_locations: Mapped[list["Location"]] = relationship(back_populates="institution", lazy="noload")

