from pydantic import EmailStr, BaseModel
from src.models import UkrainianPhoneNumber


class InstitutionInfo(BaseModel):
    id: int
    name: str
    address: str
    is_default: bool
    contact_phone: UkrainianPhoneNumber
    contact_email: EmailStr

class InstitutionCreate(BaseModel):
    name: str
    address: str
    is_default: bool
    contact_phone: UkrainianPhoneNumber
    contact_email: EmailStr

class InstitutionUpdate(BaseModel):
    id: int
    name: str | None = None
    address: str | None = None
    is_default: bool | None = None
    contact_phone: UkrainianPhoneNumber | None = None
    contact_email: EmailStr | None = None

class InstitutionDelete(BaseModel):
    id: int
