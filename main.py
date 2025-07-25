# RouteAPI by Vitaliy Khrenov
# GitLAb: https://gitlab.com/vitaliy.khrenov/routeapi 
#
# VK 2024-2025

import multiprocessing
import logging
import os
import shutil
import uvicorn

from fastapi import FastAPI, Request
from src.api import built_v1 as built

from src.api import main_router
from src.utils.observability import PrometheusMiddleware, metrics
from gunicorn.app.base import BaseApplication
from prometheus_client import multiprocess
from contextlib import asynccontextmanager
from src.databases.redis_cache import redis_startup
from fastapi import HTTPException
from authx.exceptions import AuthXException

def number_of_workers():
    return multiprocessing.cpu_count()*2 

APP_NAME = os.environ.get("APP_NAME", "ALL")
EXPOSE_PORT = os.environ.get("EXPOSE_PORT", 8180)
WORKERS = os.environ.get("FASTAPIWORKERS", number_of_workers())

def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

@asynccontextmanager
async def lifespan(app: FastAPI):
 
    redis_startup() 
   
    pmd = os.environ["PROMETHEUS_MULTIPROC_DIR"]
    if os.path.isdir(pmd):
        for filename in os.listdir(pmd):
            file_path = os.path.join(pmd, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
    yield

app = FastAPI(
    title="Route API",
    version=built,
    lifespan=lifespan
)

app.include_router(main_router)

# Setting metrics middleware
app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)
app.add_route("/metrics", metrics)

# Configure logging
logger = logging.getLogger("app")

@app.exception_handler(AuthXException)
async def authx_exception_handler(request: Request, exc: AuthXException):
    raise HTTPException(
        status_code=401,
        detail=f"AuthXException Error: {str(exc)}"
    )

if __name__ == "__main__":
    logger.info(f"Starting RouteAPI {built} on port {EXPOSE_PORT} with {WORKERS} workers")
    options = {
        "bind": "%s:%s" % ("0.0.0.0", EXPOSE_PORT),
        "workers":  WORKERS,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "forwarded_allow_ips": "*", 
        "proxy_headers": True
    }
    StandaloneApplication(app, options).run()

    #import sys
    # Use 1 worker for tests or local dev
    #if "pytest" in sys.modules:
    #    uvicorn.run("main:app", host="0.0.0.0", port=int(EXPOSE_PORT), workers=1)
    #else:
    #    uvicorn.run("main:app", host="0.0.0.0", port=int(EXPOSE_PORT), workers=WORKERS)

