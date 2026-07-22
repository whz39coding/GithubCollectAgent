from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router
from backend.core.config import PROJECT_ROOT
from backend.database.engine import init_db


app = FastAPI(title="GitHub Insight Agent API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


public_dir = PROJECT_ROOT / "backend" / "public"
assets_dir = public_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/", response_model=None)
def index():
    index_file = public_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "GitHub Insight Agent API is running. Open /docs for Swagger UI."}


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def spa_fallback(full_path: str):
    index_file = public_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend build not found."}
