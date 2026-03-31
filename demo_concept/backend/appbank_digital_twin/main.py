from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from appbank_digital_twin.api.routes.health import router as health_router
from appbank_digital_twin.api.routes.mock_actions import router as mock_actions_router
from appbank_digital_twin.api.routes.streaming import router as streaming_router
from appbank_digital_twin.core.config import get_settings


settings = get_settings()
static_dir = Path(__file__).resolve().parent / "web"

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(mock_actions_router, prefix=settings.api_prefix)
app.include_router(streaming_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
	return FileResponse(static_dir / "index.html")
