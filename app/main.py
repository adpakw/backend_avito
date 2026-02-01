from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, status

from app.repositories.model import get_model, model_client
from app.routes import predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_client.initialize_model()
    yield


app = FastAPI(lifespan=lifespan)
router = APIRouter()


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {"message": "Hello world!"}


@router.get("/health")
def health(model=Depends(get_model)):
    return {"status": "healthy", "model_loaded": model is not None}


app.include_router(router)
app.include_router(predict.router)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
