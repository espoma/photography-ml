from contextlib import asynccontextmanager
from typing import Annotated, List
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.database import create_db_and_tables, get_session
from app.models import Image, ImageCreate, ImagePublic, ImageUpdate

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

# 3. Define Routes

@app.get("/")
def read_root():
    """
    A simple health check endpoint.
    """
    return {"message": "Welcome to the Photography LLM Ops API!", "status": "active"}

@app.post("/images/", response_model=ImagePublic)
def create_image(image: ImageCreate, session: Session = Depends(get_session)):
    """
    Create a new image record in the database.
    """
    # Convert the Pydantic model (ImageCreate) to the Database model (Image)
    db_image = Image.model_validate(image)
    
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
    db_image.sqlmodel_update(update_data)
    
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
