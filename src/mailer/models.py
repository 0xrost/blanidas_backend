from pydantic import BaseModel

class LowStockMessagePayload(BaseModel):
    receiver_username: str

    spare_part_name: str

    spare_part_current_quantity: int
    spare_part_min_quantity: int

class RepairRequestCreatedMessagePayload(BaseModel):
    receiver_username: str

    equipment_name: str
    institution_name: str
    repair_request_issue: str
    repair_request_urgency: str
    was_merged: bool

    repair_request_photos: list[str]
    repair_request_url: str
