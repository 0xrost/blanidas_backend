from sqlalchemy import select, func, or_, case, Select, nulls_last
from sqlalchemy.orm import aliased

from src.equipment.schemas import Equipment
from src.equipment_model.schemas import EquipmentModel
from src.sorting import Sorting, SortingRelatedFieldsMap, SortOrder, apply_sorting
from src.repair_request.schemas import RepairRequest, RepairRequestStatus, Urgency, RepairRequestEntry


def apply_repair_request_sorting(stmt: Select, sorting: Sorting, related_fields: SortingRelatedFieldsMap) -> Select:
    if sorting.sort_by == "created_at":
        created_at_ordering = RepairRequest.created_at.desc() if sorting.sort_order == SortOrder.descending else RepairRequest.created_at.asc()
        stmt = stmt.order_by(created_at_ordering)

    if sorting.sort_by == "updated_at":
        updated_at_ordering = nulls_last(RepairRequest.updated_at.desc() if sorting.sort_order == SortOrder.descending else RepairRequest.updated_at.asc())
        stmt = stmt.order_by(updated_at_ordering)

    if sorting.sort_by == "equipment_model_name":
        equipment_alias = aliased(Equipment)
        equipment_model_alias = aliased(EquipmentModel)


        stmt = (stmt
            .join(equipment_alias, RepairRequest.equipment_id == equipment_alias.id)
            .join(equipment_model_alias, equipment_alias.equipment_model_id == equipment_model_alias.id)
            .order_by(
                equipment_model_alias.name.desc()
                if sorting.sort_order == SortOrder.descending
                else equipment_model_alias.name.asc()
            )
        )

    if sorting.sort_by == "status":
        status_order = case(
            (RepairRequest.last_status == RepairRequestStatus.not_taken, 1),
            (RepairRequest.last_status == RepairRequestStatus.waiting_engineer, 2),
            (RepairRequest.last_status == RepairRequestStatus.in_progress, 3),
            (RepairRequest.last_status == RepairRequestStatus.waiting_spare_parts, 4),
            (RepairRequest.last_status == RepairRequestStatus.finished, 5),
        )

        stmt = stmt.order_by(status_order.desc() if sorting.sort_order == SortOrder.descending else status_order.asc())

    if sorting.sort_by == "urgency":
        urgency_case = case((RepairRequest.urgency == Urgency.critical, 1), else_=0)
        stmt = stmt.order_by(urgency_case.desc() if sorting.sort_order == SortOrder.descending else urgency_case.asc())


    stmt = apply_sorting(stmt, sorting, related_fields)
    return stmt
