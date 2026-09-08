"""Admin routes — full user management for admin, limited for manager."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.database import get_db, User
from backend.app.schemas.user import UserInfo
from backend.app.middleware.auth import (
    hash_password, get_current_user, require_role
)

router = APIRouter()


class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    role: str = Field("user", pattern="^(user|manager|admin)$")


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(user|manager|admin)$")


class UpdateUserRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, pattern="^(user|manager|admin)$")


# ============ ADMIN ONLY ============

@router.get("/users", response_model=List[UserInfo])
def list_all_users(
    current_user: User = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db)
):
    """Admin: list all users. Manager: list all users (read-only)."""
    users = db.query(User).all()
    return [UserInfo(id=u.id, name=u.name, email=u.email, role=u.role) for u in users]


@router.post("/users", response_model=UserInfo)
def create_user(
    data: CreateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Admin only: create a new user with any role."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserInfo(id=user.id, name=user.name, email=user.email, role=user.role)


@router.put("/users/{user_id}", response_model=UserInfo)
def update_user(
    user_id: int,
    data: UpdateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Admin only: update user name, email, or role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        existing = db.query(User).filter(User.email == data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already taken")
        user.email = data.email
    if data.role is not None:
        user.role = data.role

    db.commit()
    db.refresh(user)
    return UserInfo(id=user.id, name=user.name, email=user.email, role=user.role)


@router.put("/users/{user_id}/role", response_model=UserInfo)
def update_user_role(
    user_id: int,
    data: UpdateRoleRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Admin only: change a user's role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user.role = data.role
    db.commit()
    db.refresh(user)
    return UserInfo(id=user.id, name=user.name, email=user.email, role=user.role)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Admin only: delete a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"detail": f"User {user.name} deleted successfully"}


# ============ MANAGER + ADMIN ============

@router.get("/users/stats")
def user_stats(
    current_user: User = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db)
):
    """Admin + Manager: get user statistics."""
    total = db.query(User).count()
    admins = db.query(User).filter(User.role == "admin").count()
    managers = db.query(User).filter(User.role == "manager").count()
    users = db.query(User).filter(User.role == "user").count()
    return {
        "total": total,
        "admin": admins,
        "manager": managers,
        "user": users
    }


@router.get("/users/{user_id}", response_model=UserInfo)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db)
):
    """Admin + Manager: view a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInfo(id=user.id, name=user.name, email=user.email, role=user.role)
