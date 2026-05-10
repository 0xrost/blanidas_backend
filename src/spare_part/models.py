from pydantic import BaseModel

from src.equipment_model.models import EquipmentModelInfo
from src.institution.models import InstitutionInfo
from src.spare_part.schemas import StockStatus
from src.spare_part_category.models import SparePartCategoryInfo


class LocationInfo(BaseModel):
    id: int
    new_quantity: int
    restored_quantity: int
    institution: InstitutionInfo | None

class CreateLocation(BaseModel):
    new_quantity: int
    restored_quantity: int
    institution_id: int

class SparePartInfo(BaseModel):
    id: int
    name: str
    min_quantity: int
    total_quantity: int
    stock_status: StockStatus
    compatible_models: list[EquipmentModelInfo]

    locations: list[LocationInfo]
    spare_part_category: SparePartCategoryInfo | None

class SparePartCreate(BaseModel):
    name: str
    min_quantity: int
    compatible_models_ids: list[int]
    spare_part_category_id: int

class SparePartUpdate(BaseModel):
    id: int
    name: str | None = None
    serial_number: str | None = None
    min_quantity: int | None = None
    compatible_models_ids: list[int] | None = None

    locations: list[CreateLocation] | None = None

    institution_id: int | None = None
    spare_part_category_id: int | None = None

class SparePartDelete(BaseModel):
    id: int
