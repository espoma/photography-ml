from contextlib import asynccontextmanager
from typing import Annotated, List
from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from app.database import create_db_and_tables, get_session
from app.models import Image, ImageCreate, ImagePublic, ImageUpdate
from app.services.ml_service import generate_tags
import shutil
import uuid
from pathlib import Path

# 1. The Lifespan Context Manager
# This is the modern way to run code when the app starts or stops.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if they don't exist
    print("🚀 Starting up... Creating database tables...")
    create_db_and_tables()
    
    # Ensure static directory exists
    static_dir = Path("static/images")
    static_dir.mkdir(parents=True, exist_ok=True)
    
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

# Configure CORS to allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js frontend
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Mount the static directory to serve images
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. Define Routes

@app.get("/")
def read_root():
    """
    A simple health check endpoint.
    """
    return {"message": "Welcome to the Photography LLM Ops API!", "status": "active"}

@app.post("/images/", response_model=ImagePublic)
async def create_image(
    file: UploadFile = File(...),
    description: str = Form(None),
    # Accepts multiple tags keys: tags=a&tags=b
    tags: List[str] = Form([]), 
    session: Session = Depends(get_session)
):
    """
    Upload a new image and create a record in the database.
    """
    # 1. Generate a unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_location = Path("static/images") / unique_filename
    
    # 2. Save the file to disk
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 3. Generate AI Tags
    ai_tags = generate_tags(str(file_location))
    combined_tags = list(set(tags + ai_tags)) # Unique tags
        
    # 4. Create the database record
    # Note: We construct the Image object directly since we are handling file upload manually
    db_image = Image(
        filename=unique_filename,
        file_path=f"/static/images/{unique_filename}",
        description=description,
        tags=combined_tags
    )
    
    # Add to the session and commit
    session.add(db_image)
    session.commit()
    
    # Refresh to get the generated ID and default values (like created_at)
    session.refresh(db_image)
    
    return db_image

@app.get("/images/", response_model=List[ImagePublic])
def read_images(
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    session: Session = Depends(get_session)
):
    """
    Get a list of images with pagination.
    """
    images = session.exec(select(Image).offset(offset).limit(limit)).all()
    return images

@app.get("/images/{image_id}", response_model=ImagePublic)
def read_image(image_id: int, session: Session = Depends(get_session)):
    """
    Get a specific image by ID.
    """
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image

@app.patch("/images/{image_id}", response_model=ImagePublic)
def update_image(image_id: int, image: ImageUpdate, session: Session = Depends(get_session)):
    """
    Update an image record. Only provided fields will be updated.
    """
    db_image = session.get(Image, image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Convert the update data to a dict, excluding unset values
    update_data = image.model_dump(exclude_unset=True)
    
    # Update the database object with the new data
    for key, value in update_data.items():
        setattr(db_image, key, value)
    
    session.add(db_image)
    session.commit()
    session.refresh(db_image)
    return db_image

@app.delete("/images/{image_id}")
def delete_image(image_id: int, session: Session = Depends(get_session)):
    """
    Delete an image record.
    """
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    session.delete(image)
    session.commit()
    
    return {"ok": True}
