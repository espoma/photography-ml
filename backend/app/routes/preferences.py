from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, UserPreference
from app.security import get_current_user

router = APIRouter(prefix="/users/me/preferences", tags=["preferences"])


class PreferenceUpsert(BaseModel):
    key: str
    value: Any


class PreferenceResponse(BaseModel):
    key: str
    value: Any


@router.get("/", response_model=list[PreferenceResponse])
def get_preferences(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return all stored preferences for the authenticated user."""
    prefs = session.exec(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    ).all()
    return [PreferenceResponse(key=p.key, value=p.value) for p in prefs]


@router.put("/", response_model=PreferenceResponse)
def upsert_preference(
    body: PreferenceUpsert,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Create or update a single preference key for the authenticated user."""
    existing = session.exec(
        select(UserPreference).where(
            UserPreference.user_id == current_user.id,
            UserPreference.key == body.key,
        )
    ).first()

    if existing:
        existing.value = body.value
        from datetime import datetime
        existing.updated_at = datetime.utcnow()
        session.add(existing)
    else:
        pref = UserPreference(user_id=current_user.id, key=body.key, value=body.value)
        session.add(pref)

    session.commit()
    return PreferenceResponse(key=body.key, value=body.value)


@router.delete("/{key}", status_code=200)
def delete_preference(
    key: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Delete a preference key."""
    pref = session.exec(
        select(UserPreference).where(
            UserPreference.user_id == current_user.id,
            UserPreference.key == key,
        )
    ).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    session.delete(pref)
    session.commit()
    return {"ok": True}
