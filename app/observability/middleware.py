import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.observability.metrics import REQUEST_DURATION_SECONDS, REQUESTS_TOTAL


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.time() - start_time
            REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(
                duration
            )

            REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint, status=status_code
            ).inc()
