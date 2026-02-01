from pydantic import BaseModel, Field


class AdvertisementWithSeller(BaseModel):
    seller_id: int = Field(ge=0)
    is_verified_seller: bool
    item_id: int = Field(ge=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: int = Field(ge=0)
    images_qty: int = Field(ge=0)


class Advertisement(BaseModel):
    seller_id: int = Field(ge=0)
    id: int = Field(ge=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: int = Field(ge=0)
    images_qty: int = Field(ge=0)

class AdvertisementID(BaseModel):
    id: int = Field(ge=0)