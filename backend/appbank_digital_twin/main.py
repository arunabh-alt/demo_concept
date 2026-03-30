from fastapi import FastAPI

from appbank_digital_twin.api.routes.agents import router as agents_router
from appbank_digital_twin.api.routes.health import router as health_router
from appbank_digital_twin.api.routes.streaming import router as streaming_router
from appbank_digital_twin.core.config import get_settings


settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(agents_router, prefix=settings.api_prefix)
app.include_router(streaming_router, prefix=settings.api_prefix)
