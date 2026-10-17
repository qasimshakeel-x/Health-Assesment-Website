"""Admin routes — full user management for admin, limited for manager."""
import os
import sys
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.database import get_db, SessionLocal, User, AdminActionLog
from backend.app.schemas.user import UserInfo
from backend.app.middleware.auth import (
    hash_password, get_current_user, require_role
)

router = APIRouter()


def _log_action(db: Session, admin_id: Optional[int], action: str,
                target: Optional[str] = None, details: Optional[str] = None):
    """Admin action ko audit table mein likho (best-effort — failure se request na toote)."""
    try:
        db.add(AdminActionLog(admin_id=admin_id, action=action, target=target, details=details))
        db.commit()
    except Exception:
        db.rollback()


def _run_retrain(action_id: int, admin_id: int):
    """Background: saare ML models retrain karo, phir live pipeline reload karo."""
    db = SessionLocal()
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        # ML_TRAINING.md §7: single config-driven trainer (ml/train.py) replaced the old
        # ml/training/train_models.py synthetic generator pipeline.
        from ml.train import train_all
        train_all()
        from backend.app.main import ml_pipeline
        ml_pipeline.load_models()
        row = db.query(AdminActionLog).filter(AdminActionLog.id == action_id).first()
        if row:
            row.details = "retrain complete — models reloaded"
            db.commit()
    except Exception as exc:
        try:
            row = db.query(AdminActionLog).filter(AdminActionLog.id == action_id).first()
            if row:
                row.details = f"retrain failed: {exc}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


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
    _log_action(db, current_user.id, "create_user", user.email, f"role={user.role}")
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
    _log_action(db, current_user.id, "update_user", user.email)
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
    _log_action(db, current_user.id, "update_role", user.email, f"role={user.role}")
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
    _log_action(db, current_user.id, "delete_user", user.email)
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


# ============ MODEL ADMIN (05-API-SPEC §7) ============

@router.post("/models/retrain", status_code=202)
def retrain_models(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Admin only: retrain all ML models in background, then reload live pipeline."""
    log = AdminActionLog(admin_id=current_user.id, action="retrain_models",
                         target="all-models", details="retrain started")
    db.add(log)
    db.commit()
    db.refresh(log)

    background_tasks.add_task(_run_retrain, log.id, current_user.id)
    return {"action_id": log.id, "status": "started",
            "message": "Model retraining started in background"}


@router.get("/actions")
def list_admin_actions(
    limit: int = 100,
    current_user: User = Depends(require_role("admin", "manager")),
    db: Session = Depends(get_db)
):
    """Admin + Manager: recent admin/manager actions (audit log)."""
    limit = max(1, min(500, limit))
    rows = (
        db.query(AdminActionLog)
        .order_by(AdminActionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    admin_ids = {r.admin_id for r in rows if r.admin_id}
    admins = {u.id: u for u in db.query(User).filter(User.id.in_(admin_ids)).all()} if admin_ids else {}
    return {
        "actions": [
            {
                "id": r.id,
                "admin_id": r.admin_id,
                "admin_email": admins[r.admin_id].email if r.admin_id in admins else None,
                "action": r.action,
                "target": r.target,
                "details": r.details,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]
    }
