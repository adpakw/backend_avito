from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.clients.kafka import kafka_producer
from app.clients.redis import redis_client
from app.observability.middleware import PrometheusMiddleware
from app.repositories.model import get_model, model_client
from app.routes import auth, close, moderation_result, predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_client.initialize_model()
    await kafka_producer.start()
    await redis_client.start()
    yield
    await kafka_producer.stop()
    await redis_client.stop()


app = FastAPI(lifespan=lifespan)
router = APIRouter()
app.add_middleware(PrometheusMiddleware)


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {"message": "Hello world!"}


@router.get("/health")
def health(model=Depends(get_model)):
    return {"status": "healthy", "model_loaded": model is not None}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(router)
app.include_router(predict.router)
app.include_router(moderation_result.router)
app.include_router(close.router)
app.include_router(auth.router, prefix="/auth", tags=["authentication"])


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
