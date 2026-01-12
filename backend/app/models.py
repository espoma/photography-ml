from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, String
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import ARRAY

class Image(SQLModel, table=True):
    """
    Represents an Image in our database.
    """
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    file_path: str
    
    # Store tags as a list of strings (PostgreSQL Array)
    tags: List[str] = Field(default=[], sa_column=Column(ARRAY(String)))
    
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
