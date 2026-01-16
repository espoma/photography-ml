from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, String
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ARRAY

# Base class with shared fields
class ImageBase(SQLModel):
    filename: str
    file_path: str
    tags: List[str] = Field(default=[])
    description: Optional[str] = None

# Database Table Model
class Image(ImageBase, table=True):
    """
    Represents an Image in our database.
    """
    id: int | None = Field(default=None, primary_key=True)
    # We need to redefine tags here to apply the sa_column for PostgreSQL ARRAY
    tags: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Schema for Creating an Image (Client -> Server)
class ImageCreate(ImageBase):
    pass

# Schema for Updating an Image (Client -> Server)
class ImageUpdate(SQLModel):
    filename: str | None = None
    file_path: str | None = None
    tags: List[str] | None = None
    description: str | None = None

# Schema for Reading an Image (Server -> Client)
class ImagePublic(ImageBase):
    id: int
    created_at: datetime
