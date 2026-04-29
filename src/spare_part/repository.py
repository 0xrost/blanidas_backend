
from sqlalchemy import update, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.decorators import integrity_errors
from src.institution.schemas import Institution
from src.sorting import apply_sorting_wrapper, SortingRelatedField
from src.exceptions import DomainError, DomainErrorCode
from src.repository import CRUDRepository
from src.spare_part.filters import apply_spare_parts_filters
from src.spare_part.models import SparePartCreate, SparePartUpdate
from src.spare_part.schemas import SparePart, EquipmentModelSparePart, Location
from src.spare_part.sorting import apply_spare_parts_sorting
from src.filters import apply_filters_wrapper, FilterRelatedField

filter_related_fields_map = {
    "name": FilterRelatedField(column=SparePart.name),
    "spare_part_category_id": FilterRelatedField(column=SparePart.spare_part_category_id),
    "compatible_model_id": None,
    "institution_id": None,
    "stock_status": None,
}

sorting_related_fields_map = {
    "name": SortingRelatedField(column=SparePart.name),
    "quantity": None,
    "stock_status": None,
}

class SparePartRepository(CRUDRepository[SparePart]):
    def __init__(self):
        super().__init__(
            SparePart,
            filter_callback=apply_filters_wrapper(apply_spare_parts_filters, filter_related_fields_map),
            sorting_callback=apply_sorting_wrapper(apply_spare_parts_sorting, sorting_related_fields_map),
        )

    @staticmethod
    async def get_by_ids(ids: list[int], database: AsyncSession) -> list[SparePart]:
        result = (await database.execute(select(SparePart).where(SparePart.id.in_(ids)))).scalars().all()
        return list(result)

    @integrity_errors()
    async def create(self, data: dict, database: AsyncSession, preloads: list[str] | None = None) -> SparePart:
        data_model = SparePartCreate.model_validate(data)
        del data["compatible_models_ids"]

        row_id = (await database.execute(insert(SparePart).values(data).returning(SparePart.id))).scalar()

        for compatible_model_id in data_model.compatible_models_ids:
            await database.execute(insert(EquipmentModelSparePart).values({
                "equipment_model_id": compatible_model_id,
                "spare_part_id": row_id,
            }))

        institutions = (await database.execute(select(Institution).where(Institution.is_default))).scalars().all()
        for institution in institutions:
            location_db = Location(
                quantity=0,
                restored_quantity=0,
                spare_part_id=row_id,
                institution_id=institution.id,
            )

            database.add(location_db)

        await database.commit()
        return await self.get(row_id, database, preloads)

    @integrity_errors()
    async def update(self, id_: int, data: dict, database: AsyncSession, preloads: list[str] | None = None) -> SparePart:
        data_model = SparePartUpdate.model_validate(data)

        fields_to_update = data_model.model_dump(exclude={"locations", "compatible_models_ids"}, exclude_unset=True)
        rows = await database.execute(update(SparePart).where(SparePart.id == id_).values(fields_to_update))
        if rows.rowcount == 0:
            raise DomainError(DomainErrorCode.not_entity)

        if data_model.compatible_models_ids is not None:
            await database.execute(delete(EquipmentModelSparePart).where(EquipmentModelSparePart.spare_part_id == id_))
            for compatible_model_id in data_model.compatible_models_ids:
                await database.execute(insert(EquipmentModelSparePart).values({
                    "equipment_model_id": compatible_model_id,
                    "spare_part_id": id_,
                }))

        if data_model.locations is not None:
            await database.execute(delete(Location).where(Location.spare_part_id == id_))
            for location in data_model.locations:
                await database.execute(insert(Location).values({
                    "quantity": location.quantity,
                    "restored_quantity": location.restored_quantity,
                    "institution_id": location.institution_id,
                    "spare_part_id": id_,
                }))

        await database.commit()
        return await self.get(id_, database, preloads)


