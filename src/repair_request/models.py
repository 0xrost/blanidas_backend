from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from src.auth.models import UserInfo
from src.equipment.models import EquipmentInfo
from src.failure_type.models import FailureTypeInfo
from src.institution.models import InstitutionInfo
from src.repair_request.schemas import Urgency, RepairRequestStatus
from src.spare_part.models import SparePartInfo


class RepairRequestStatusRecordInfo(BaseModel):
    id: int
    was_merged: bool
    created_at: datetime
    status: RepairRequestStatus
    assigned_engineer: UserInfo | None

class RepairRequestStatusRecordCreate(BaseModel):
    status: RepairRequestStatus
    assigned_engineer_id: int | None

class FileCreate(BaseModel):
    file_path: str
    repair_request_id: int

class FileInfo(BaseModel):
    file_path: str

class UsedSparePartCreate(BaseModel):
    new_quantity: int
    restored_quantity: int = 0
    note: str
    spare_part_id: int
    institution_id: int

class UsedSparePartInfo(BaseModel):
    new_quantity: int
    restored_quantity: int = 0
    note: str
    spare_part: SparePartInfo | None
    institution: InstitutionInfo | None

class RepairRequestEntryInfo(BaseModel):
    id: int
    issue: str
    photos: list[FileInfo]
    created_at: datetime

class RepairRequestInfo(BaseModel):
    id: int
    urgency: Urgency
    manager_note: str | None
    engineer_note: str | None
    created_at: datetime
    completed_at: datetime | None
    updated_at: datetime | None
    last_status: RepairRequestStatus
    entries: list[RepairRequestEntryInfo]

    failure_types: list[FailureTypeInfo]
    used_spare_parts: list[UsedSparePartInfo]
    status_history: list[RepairRequestStatusRecordInfo]
    equipment: EquipmentInfo | None

class RepairRequestCreate(BaseModel):
    issue: str
    urgency: Urgency
    equipment_id: int

class RepairRequestUpdate(BaseModel):
    id: int
    manager_note: str | None = None
    engineer_note: str | None = None
    assigned_engineer_id: str | None = None

    failure_types_ids: list[int] | None = None
    used_spare_parts: list[UsedSparePartCreate] | None = None
    status_history: RepairRequestStatusRecordCreate | None = None
