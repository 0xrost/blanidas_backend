from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import aliased

from src.auth.schemas import User, Role
from src.equipment.schemas import Equipment, EquipmentStatus
from src.institution.schemas import Institution
from src.repair_request.schemas import RepairRequestStatus, RepairRequestStatusRecord, RepairRequest
from src.spare_part.schemas import SparePart, Location, StockStatus
from src.summary.models import UserSummary, InstitutionSummary, EquipmentSummary, SparePartSummary, RepairRequestSummary


equipment_rules = {
    "total": lambda db: db.scalar(select(func.count()).select_from(Equipment)),
    "working": lambda db: db.scalar(select(func.count()).select_from(Equipment).where(Equipment.status == EquipmentStatus.working.value)),
    "under_maintenance": lambda db: db.scalar(select(func.count()).select_from(Equipment).where(Equipment.status == EquipmentStatus.under_maintenance.value)),
    "not_working": lambda db: db.scalar(select(func.count()).select_from(Equipment).where(Equipment.status == EquipmentStatus.not_working.value)),
}

spare_part_rules = {
    "total": lambda db: db.scalar(select(func.count()).select_from(SparePart)),
    "in_stock": lambda db: db.scalar(select(func.count()).select_from(SparePart).where(SparePart.stock_status == StockStatus.in_stock.value)),
    "low_stock": lambda db: db.scalar(select(func.count()).select_from(SparePart).where(SparePart.stock_status == StockStatus.low_stock.value)),
    "out_of_stock": lambda db: db.scalar(select(func.count()).select_from(SparePart).where(SparePart.stock_status == StockStatus.out_of_stock.value)),
    "new": lambda db: db.scalar(select(func.sum(Location.new_quantity)).select_from(Location)),
    "restored": lambda db: db.scalar(select(func.sum(Location.restored_quantity)).select_from(Location)),
}

repair_part_rules = {
    "all": lambda db: db.scalar(select(func.count()).select_from(RepairRequest)),
    "new": lambda db: db.scalar(
        select(func.count())
        .select_from(RepairRequest)
        .where(RepairRequest.last_status == RepairRequestStatus.not_taken.value)
    ),
    "waiting_engineer": lambda db: db.scalar(
        select(func.count())
        .select_from(RepairRequest)
        .where(RepairRequest.last_status == RepairRequestStatus.waiting_engineer.value)
    ),
    "in_progress": lambda db: db.scalar(
        select(func.count())
        .select_from(RepairRequest)
        .where(RepairRequest.last_status == RepairRequestStatus.in_progress.value)
    ),
    "waiting_spare_parts": lambda db: db.scalar(
        select(func.count())
        .select_from(RepairRequest)
        .where(RepairRequest.last_status == RepairRequestStatus.waiting_spare_parts.value)
    ),
    "finished": lambda db: db.scalar(
        select(func.count())
        .select_from(RepairRequest)
        .where(RepairRequest.last_status == RepairRequestStatus.finished.value)
    )
}


SUMMARY_RULES = {
    "repair-requests": {
        "response_model": RepairRequestSummary,
        "rules": repair_part_rules,
    },
    "spare-parts": {
        "response_model": SparePartSummary,
        "rules": spare_part_rules,
    },
    "equipment": {
        "response_model": EquipmentSummary,
        "rules": equipment_rules,
    },
}
