"""
Idempotent demo account seeder.
Creates the demo user only if it doesn't already exist.
Safe to run on every container startup.

Usage:
  Set DEMO_EMAIL and DEMO_PASSWORD environment variables, then run:
    DEMO_EMAIL=you@example.com DEMO_PASSWORD=your-secure-password python seed_demo.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.user import User
from passlib.context import CryptContext

try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def seed_demo_account():
    demo_email = os.environ.get("DEMO_EMAIL")
    demo_password = os.environ.get("DEMO_PASSWORD")

    if not demo_email or not demo_password:
        print("⚠️  Set DEMO_EMAIL and DEMO_PASSWORD environment variables to seed a demo account.")
        print("   Example: DEMO_EMAIL=you@example.com DEMO_PASSWORD=your-secure-password python seed_demo.py")
        return

    if len(demo_password) < 8:
        print("⚠️  DEMO_PASSWORD must be at least 8 characters.")
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == demo_email).first()
        if existing:
            print(f"✅ Account already exists ({demo_email})")
            return

        demo_user = User(
            email=demo_email,
            name="Demo User",
            hashed_password=pwd_context.hash(demo_password),
            xp=0,
            level=1,
            is_active=True,
        )
        db.add(demo_user)
        db.commit()
        print(f"✅ Created demo account: {demo_email}")
    except Exception as e:
        print(f"⚠️  Demo seed skipped: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_account()
