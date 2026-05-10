from sqlalchemy import func, select, case, Select

from src.equipment_model.schemas import EquipmentModel
from src.filters import apply_filters, Filters, FilterRelatedFieldsMap, get_filter_value
from src.institution.schemas import Institution
from src.spare_part.models import StockStatus
from src.spare_part.schemas import SparePart, Location


def apply_spare_parts_filters(stmt: Select, filters: Filters, related_fields: FilterRelatedFieldsMap) -> Select:
    stmt = apply_filters(stmt, filters, related_fields)

    compatible_model_id = get_filter_value(filters.get("compatible_model_id"), column=EquipmentModel.id)
    institution_id = get_filter_value(filters.get("institution_id"), column=Institution.id)
    stock_status = get_filter_value(filters.get("stock_status"), enum=StockStatus)

    if stock_status is not None:
        subquery = (
            select(
                Location.spare_part_id.label("spare_part_id"),
                func.sum(Location.new_quantity + Location.restored_quantity).label("total_quantity"),
            )
            .group_by(Location.spare_part_id)
            .subquery()
        )

        total_quantity = func.coalesce(subquery.c.total_quantity, 0)

        stock_case = case(
            (total_quantity == 0, StockStatus.out_of_stock.value),
            (total_quantity <= SparePart.min_quantity, StockStatus.low_stock.value),
            else_=StockStatus.in_stock.value,
        )

        stmt = (
            stmt
            .outerjoin(subquery, subquery.c.spare_part_id == SparePart.id)
            .where(stock_case == stock_status)
        )

    if compatible_model_id is not None:
        stmt = stmt.where(SparePart.compatible_models.any(EquipmentModel.id == compatible_model_id))
    if institution_id is not None:
        stmt = stmt.where(SparePart.locations.any(Location.institution_id == int(institution_id)))

    return stmt
