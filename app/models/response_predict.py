from pydantic import BaseModel, Field


class PredictResponse(BaseModel):
    is_violation: int
    probability: float
