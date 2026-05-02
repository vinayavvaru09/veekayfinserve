from fastapi import APIRouter

from app.api.v1.endpoints import logs, notices, policies, providers, templates

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(policies.router)
api_router.include_router(providers.router)
api_router.include_router(notices.router)
api_router.include_router(templates.router)
api_router.include_router(logs.router)
