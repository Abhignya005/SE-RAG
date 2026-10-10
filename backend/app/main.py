from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from app.api.projects import router as projects_router
from app.api.requirements import router as requirements_router
from app.api.artifacts import router as artifacts_router
from app.api.auth import router as auth_router
from app.db.mongodb import connect_to_mongo, close_mongo_connection
import contextlib
import os

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET") == "change-me":
        raise RuntimeError("JWT_SECRET must be configured before starting the API")
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="AI Software Engineering Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:5174,http://127.0.0.1:5174",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(requirements_router, prefix="/requirements", tags=["requirements"])
app.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Software Engineering Assistant API"}
