import uvicorn
from fastapi import FastAPI, status

from app.pydantic_models import Advertisement, PredictionResult

app = FastAPI()


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {"message": "Hello world!"}


@app.post("/predict", response_model=PredictionResult, status_code=status.HTTP_200_OK)
async def predict(ad: Advertisement) -> PredictionResult:
    if ad.is_verified_seller:
        return PredictionResult(result=True)
    elif ad.images_qty > 0:
        return PredictionResult(result=True)
    else:
        return PredictionResult(result=False)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
