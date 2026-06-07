from __future__ import annotations
from typing import Optional, List, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, String, Relationship
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import ARRAY


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column(String, unique=True))
    email: Optional[str] = Field(default=None, sa_column=Column(String, unique=True))
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserPreference(SQLModel, table=True):
    """Stores per-user preferences that persist across sessions.

    key examples: "theme_weights", "preferred_group_size", "style_emphasis"
    value: arbitrary JSON (dict or list)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    key: str = Field(sa_column=Column(String, index=True))
    value: Any = Field(default=None, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ImageBase(SQLModel):
    filename: str
    file_path: str
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class Image(ImageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tags: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    # 768-dim float vector from text-embedding-004 (or None until generated)
    embedding: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")


class ImageCreate(ImageBase):
    pass


class ImageUpdate(SQLModel):
    filename: Optional[str] = None
    file_path: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class ImagePublic(ImageBase):
    id: int
    created_at: datetime
    user_id: Optional[int] = None
    embedding: Optional[List[float]] = None
