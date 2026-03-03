from pydantic import BaseModel


class PredictResponse(BaseModel):
    is_violation: int
    probability: float
