from typing import Optional

from pydantic import BaseModel, Field
import datetime


class ModerationMessage(BaseModel):
    task_id: int = Field(ge=0)
    status: str = Field(pattern="^(pending|completed|failed)$")
    message: str = Field(min_length=1)


class ModerationResult(BaseModel):
    task_id: int = Field(ge=0)
    status: str = Field(pattern="^(pending|completed|failed)$")
    is_violation: Optional[bool] = Field(None)
    probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
    )


class Moderation(BaseModel):
    id: int = Field(ge=0)
    item_id: int = Field(ge=0)
    status: str = Field(pattern="^(pending|completed|failed)$")
    is_violation: Optional[bool] = Field(None)
    probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
    )
    error_message: Optional[str] = Field(None)
    created_at: datetime.datetime
    processed_at: Optional[datetime.datetime]
