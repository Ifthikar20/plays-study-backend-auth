"""
Idempotent demo account seeder for Django.
Creates the demo user only if it doesn't already exist.
Safe to run on every container startup.

Usage:
  DEMO_EMAIL=you@example.com DEMO_PASSWORD=YourPass123! python seed_demo.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playstudy.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def seed_demo_account():
    demo_email = os.environ.get('DEMO_EMAIL')
    demo_password = os.environ.get('DEMO_PASSWORD')

    if not demo_email or not demo_password:
        print("⚠️  Set DEMO_EMAIL and DEMO_PASSWORD to seed a demo account.")
        return

    if len(demo_password) < 8:
        print("⚠️  DEMO_PASSWORD must be at least 8 characters.")
        return

    if User.objects.filter(email=demo_email).exists():
        print(f"✅ Account already exists ({demo_email})")
        return

    try:
        User.objects.create_user(
            email=demo_email,
            name='Demo User',
            password=demo_password,
        )
        print(f"✅ Created demo account: {demo_email}")
    except Exception as e:
        print(f"⚠️  Demo seed skipped: {e}")


if __name__ == '__main__':
    seed_demo_account()
