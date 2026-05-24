from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import courses, listings, matching, me, messages


app = FastAPI(title="UATX_WeChat API", version="0.1.0")


if settings.APP_ENV == "dev":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(me.router)
app.include_router(courses.router)
app.include_router(listings.router)
app.include_router(messages.router)
app.include_router(matching.router)


# When deployed on Railway, FastAPI also serves the built React app at /.
# Locally we run Vite separately, so this is a no-op unless the static dir
# exists (which happens after `npm run build` + copying frontend/dist into
# backend/static during the deploy step).
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
