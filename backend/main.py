from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_and_tables
from app.models import Image  # Import models so they are registered with SQLModel

# 1. The Lifespan Context Manager
# This is the modern way to run code when the app starts or stops.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if they don't exist
    print("🚀 Starting up... Creating database tables...")
    create_db_and_tables()
    yield
    # Shutdown: (We don't need to do anything here yet)
    print("🛑 Shutting down...")

# 2. Initialize the App
app = FastAPI(
    title="Photography LLM Ops",
    description="API for Smart Photography Portfolio",
    version="0.1.0",
    lifespan=lifespan
)

# 3. Define a Route
@app.get("/")
def read_root():
    """
    A simple health check endpoint.
    """
    return {"message": "Welcome to the Photography LLM Ops API!", "status": "active"}
