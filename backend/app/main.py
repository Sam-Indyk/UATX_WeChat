from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import classmates, courses, feedback, listings, matching, me, messages, stripe_routes, users


class SPAStaticFiles(StaticFiles):
    """Static file handler that falls back to index.html on 404.

    Required for React Router to work after a hard navigation. Without this,
    a request like /sign-in or /sign-in/sso-callback (the Clerk OAuth
    callback) hits the backend, finds no matching file, returns 404 — and
    sign-up / sign-in break for everyone.

    Paths under /api/ are deliberately NOT given the index.html fallback so
    that bad API URLs return a proper 404 instead of an HTML page (which
    would otherwise silently mask client bugs).
    """

    async def get_response(self, path: str, scope):
        # /api/* must remain real 404s. Bypass super() entirely — passing the
        # api/ path through would let StaticFiles' html=True fallback hand
        # back index.html, defeating the whole point of the guard.
        # Normalize the separator: Starlette passes os.sep-flavored paths,
        # which is '\\' on Windows during local dev.
        normalized = path.replace("\\", "/")
        if normalized == "api" or normalized.startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


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
app.include_router(classmates.router)
app.include_router(stripe_routes.router)
app.include_router(users.router)
app.include_router(feedback.router)


# When deployed on Railway, FastAPI also serves the built React app at /.
# Locally we run Vite separately, so this is a no-op unless the static dir
# exists (which happens after `npm run build` + copying frontend/dist into
# backend/static during the deploy step).
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/", SPAStaticFiles(directory=_static_dir, html=True), name="static")
