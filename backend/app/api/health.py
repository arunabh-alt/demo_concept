from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict[str, object]:
    return {
        "service": "full-stack-auth-api",
        "status": "ok",
        "message": "Backend is running. Use /docs for OpenAPI UI or /api/* endpoints for requests.",
        "routes": {
            "docs": "/docs",
            "health": "/api/health",
            "auth": "/api/auth",
            "agents": "/api/agents",
        },
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "full-stack-auth-api"}
