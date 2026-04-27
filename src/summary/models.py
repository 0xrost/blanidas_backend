from pydantic import BaseModel


class RepairRequestSummary(BaseModel):
    new: int
    in_progress: int
    waiting_spare_parts: int
    finished: int

class SparePartSummary(BaseModel):
    total: int
    in_stock: int
    low_stock: int
    out_of_stock: int
    new: int
    restored: int

class UserSummary(BaseModel):
    total: int
    engineers: int
    managers: int

class EquipmentSummary(BaseModel):
    total: int
    working: int
    under_maintenance: int
    not_working: int

class InstitutionSummary(BaseModel):
    total: int
    equipment: int

SummaryResponse = (
        UserSummary
        | EquipmentSummary
        | SparePartSummary
        | InstitutionSummary
        | RepairRequestSummary
)