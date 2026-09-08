"""Seed script — creates admin, manager accounts + initializes DB."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models.database import init_db, SessionLocal, User
from backend.app.middleware.auth import hash_password


def seed():
    """Create tables + admin + manager accounts."""
    print("Initializing database tables...")
    init_db()

    db = SessionLocal()
    try:
        accounts = [
            {"name": "Admin", "email": "admin@longevity.com", "password": "Admin@123", "role": "admin"},
            {"name": "Manager", "email": "manager@longevity.com", "password": "Manager@123", "role": "manager"},
        ]

        for acc in accounts:
            existing = db.query(User).filter(User.email == acc["email"]).first()
            if not existing:
                user = User(
                    name=acc["name"],
                    email=acc["email"],
                    password_hash=hash_password(acc["password"]),
                    role=acc["role"]
                )
                db.add(user)
                print(f"  Created {acc['role']}: {acc['email']} / {acc['password']}")
            else:
                print(f"  {acc['role']} already exists: {acc['email']}")

        db.commit()
        print("\nSeed complete!")
        print("  Admin:    admin@longevity.com / Admin@123")
        print("  Manager:  manager@longevity.com / Manager@123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
