import time
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram

REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

PREDICTIONS_TOTAL = Counter(
    "predictions_total", "Total number of predictions", ["result"]
)

PREDICTION_DURATION_SECONDS = Histogram(
    "prediction_duration_seconds",
    "Time spent on ML model inference",
    ["prediction_type"],
)

PREDICTION_ERRORS_TOTAL = Counter(
    "prediction_errors_total", "Total number of prediction errors", ["error_type"]
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
)

MODEL_PREDICTION_PROBABILITY = Histogram(
    "model_prediction_probability",
    "Distribution of prediction probabilities",
)


def track_db_query(query_type):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(
                    duration
                )

        return async_wrapper

    return decorator
