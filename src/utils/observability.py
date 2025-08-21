import time
import os

from typing import Tuple

from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp

from prometheus_client import generate_latest, REGISTRY, CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, CollectorRegistry
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from fastapi.security.utils import get_authorization_scheme_param
from fastapi import HTTPException

from src.auth.jwt import security
from http.cookies import SimpleCookie
from prometheus_client import multiprocess
from src.utils.logger import getIPAddress

ALLOWED_NETWORK_PREFIXES = ("172.1", "192.168")

INFO = Gauge(
    "fastapi_app_info", "FastAPI application information.", [
        "app_name"]
)

REQUESTS = Counter(
    "fastapi_requests_total", "Total count of requests by method and path.", [
        "method", "path", "app_name"]
)

RESPONSES = Counter(
    "fastapi_responses_total",
    "Total count of responses by method, path and status codes.",
    ["method", "path", "status_code", "app_name"],
)

REQUESTS_PROCESSING_TIME = Histogram(
    "fastapi_requests_duration_seconds",
    "Histogram of requests processing time by path (in seconds)",
    ["method", "path", "app_name"],
)

EXCEPTIONS = Counter(
    "fastapi_exceptions_total",
    "Total count of exceptions raised by path and exception type",
    ["method", "path", "exception_type", "app_name"],
)

REQUESTS_IN_PROGRESS = Gauge(
    "fastapi_requests_in_progress",
    "Gauge of requests by method and path currently being processed",
    ["method", "path", "app_name"], multiprocess_mode='livesum'
)
# Middleware for Prometheus metrics collection ---------------------------------------------------
class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, app_name: str = "fastapi-app") -> None:
        super().__init__(app)
        self.app_name = app_name
        INFO.labels(app_name=self.app_name).inc()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        path, is_handled_path = self.get_path(request)

        if not is_handled_path or not path.startswith('/v'):
            return await call_next(request)

    # Extract token from Authorization header
        cookie_header = request.headers.get("cookie")
        access_token = None
        token = None
        if cookie_header:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            if "access_token" in cookie:
                access_token = cookie["access_token"].value
                if access_token:
                    scheme, token = get_authorization_scheme_param(f"Bearer {access_token}")
        
        if not access_token:
            auth_header = request.headers.get("Authorization")
            if auth_header:
                scheme, token = get_authorization_scheme_param(auth_header)
                if token=='':
                    token, x = get_authorization_scheme_param(auth_header)                    

        username = ''
       
        if token:
            try: 
                payload = security._decode_token(token)
                username = payload.uname
            except Exception:
                pass
            
   
        if username!='':    
            INFO.labels(app_name=username).inc() 

        REQUESTS_IN_PROGRESS.labels(
            method=method, path=path, app_name=self.app_name).inc()
        if username!='':
            REQUESTS_IN_PROGRESS.labels(
                method=method, path=path, app_name=username).inc()
        if username!='':
            REQUESTS.labels(method=method, path=path, app_name=username).inc()
        REQUESTS.labels(method=method, path=path, app_name=self.app_name).inc()
        
        before_time = time.perf_counter()
        try:
            response = await call_next(request)
            
        except BaseException as e:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
            if username!='':
                EXCEPTIONS.labels(method=method, path=path, exception_type=type(e).__name__, app_name=username).inc()
            EXCEPTIONS.labels(method=method, path=path, exception_type=type(e).__name__, app_name=self.app_name).inc()
            raise e from None
        else:
            status_code = response.status_code
            after_time = time.perf_counter()
            if username!='':
                REQUESTS_PROCESSING_TIME.labels(method=method, path=path, app_name=username).observe(
                                                after_time - before_time, exemplar={'TraceID':""})
            REQUESTS_PROCESSING_TIME.labels(method=method, path=path, app_name=self.app_name).observe(
                after_time - before_time, exemplar={'TraceID':""})
            
        finally:
            if username!='':
                RESPONSES.labels(method=method, path=path,
                                 status_code=status_code, app_name=username).inc()
            RESPONSES.labels(method=method, path=path,
                             status_code=status_code, app_name=self.app_name).inc()
            if username!='':
                REQUESTS_IN_PROGRESS.labels(
                    method=method, path=path, app_name=username).dec()
            REQUESTS_IN_PROGRESS.labels(
                method=method, path=path, app_name=self.app_name).dec()

        return response

    @staticmethod
    def get_path(request: Request) -> Tuple[str, bool]:
        for route in request.app.routes:
            match, child_scope = route.matches(request.scope)
            if match == Match.FULL:
                return route.path, True

        return request.url.path, False

# Endpoint for Prometheus metrics ---------------------------------------------------------------
def metrics(request: Request) -> Response:
    
    ip_address = getIPAddress(request)
    if not ip_address.startswith(ALLOWED_NETWORK_PREFIXES):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
        pmd = os.environ["PROMETHEUS_MULTIPROC_DIR"]

        if os.path.isdir(pmd):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
        else:
            raise ValueError(
                f"Env var PROMETHEUS_MULTIPROC_DIR='{pmd}' not a directory."
            )
    else:
        registry = REGISTRY

    return Response(generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST})

# Function to set up OpenTelemetry for FastAPI -----------------------------------------------------
def setting_otlp(app: ASGIApp, app_name: str, endpoint: str, log_correlation: bool = True) -> None:

    if log_correlation:
        LoggingInstrumentor().instrument(set_logging_format=True)

    FastAPIInstrumentor.instrument_app(app)