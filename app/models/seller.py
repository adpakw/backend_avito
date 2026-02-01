from pydantic import BaseModel, Field


class Seller(BaseModel):
    id: int = Field(ge=0)
    is_verified: bool
