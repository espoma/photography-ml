from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.database import get_session
from app.models import User
from app.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    username: str
    email: str | None = None
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    access_token: str
    token_type: str = "bearer"


@router.post("/signup")
def signup(user: UserCreate, session: Session = Depends(get_session)) -> UserResponse:
    existing = session.exec(select(User).where(User.username == user.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hash_password(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    access_token = create_access_token({"sub": db_user.username})
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        access_token=access_token,
    )


@router.post("/login")
def login(payload: UserLogin, session: Session = Depends(get_session)) -> UserResponse:
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.username})
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        access_token=access_token,
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}
