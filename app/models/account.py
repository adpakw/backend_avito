from datetime import datetime

from pydantic import BaseModel, Field


class Account(BaseModel):
    id: int = Field(ge=0)
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    is_blocked: bool = Field(default=False)


class AccountCreate(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)


class AccountLogin(BaseModel):
    login: str
    password: str


class AccountResponse(BaseModel):
    id: int
    login: str
    is_blocked: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
