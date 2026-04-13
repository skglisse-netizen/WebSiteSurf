from pydantic import BaseModel
from typing import Optional

class ServiceBase(BaseModel):
    title: str
    description: str
    price: float
    image_url: Optional[str] = None
    is_active: bool = True

class ServiceCreate(ServiceBase):
    pass

class ServiceResponse(ServiceBase):
    id: int

    class Config:
        from_attributes = True

class InquiryBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    message: str

class InquiryCreate(InquiryBase):
    pass

class InquiryResponse(InquiryBase):
    id: int
    is_processed: bool

    class Config:
        from_attributes = True
