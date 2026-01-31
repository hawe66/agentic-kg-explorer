"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic KG Explorer API",
        description="REST API for the Agentic AI Knowledge Graph Explorer agent pipeline.",
        version="0.3.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
