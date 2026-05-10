from sqlalchemy import Select, select

from src.sorting import Sorting, SortingRelatedFieldsMap, SortOrder, apply_sorting
from src.spare_part.schemas import SparePart, Location


from sqlalchemy import case, and_, func
def apply_spare_parts_sorting(stmt: Select, sorting: Sorting, related_fields: SortingRelatedFieldsMap) -> Select:
    total_quantity_subq = (
        select(
            Location.spare_part_id.label("spare_part_id"),
            (func.sum(Location.new_quantity) + func.sum(Location.restored_quantity)).label("total_quantity")
        )
        .group_by(Location.spare_part_id)
        .subquery()
    )

    total_qty_col = func.coalesce(total_quantity_subq.c.total_quantity, 0)

    if sorting.sort_by == "quantity":
        return stmt.outerjoin(
            total_quantity_subq,
            SparePart.id == total_quantity_subq.c.spare_part_id
        ).order_by(
            total_qty_col.desc() if sorting.sort_order == SortOrder.descending else total_qty_col.asc()
        )


    if sorting.sort_by == "stock_status":
        status_expr = case(
            (total_qty_col > SparePart.min_quantity, 2),
            (and_(total_qty_col > 0, total_qty_col <= SparePart.min_quantity), 1),
            else_=0
        )

        return (
            stmt
            .outerjoin(total_quantity_subq, SparePart.id == total_quantity_subq.c.spare_part_id)
            .order_by(status_expr.desc() if sorting.sort_order == SortOrder.descending else status_expr.asc())
        )

    return apply_sorting(stmt, sorting, related_fields)
