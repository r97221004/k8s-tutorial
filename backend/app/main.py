from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers.todos import router as todos_router
from .schemas import Health
from .settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.cors_origins],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["*"],
        )

    @app.get("/api/healthz", response_model=Health, tags=["system"])
    async def healthz() -> Health:
        return Health(status="ok", version=settings.app_version)

    @app.get("/api/version", response_model=Health, tags=["system"])
    async def version() -> Health:
        return Health(status="ok", version=settings.app_version)

    app.include_router(todos_router, prefix="/api")
    return app


app = create_app()
