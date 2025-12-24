"""
Migration: Add pdf_content field to study_sessions table

Adds pdf_content column to store converted PDF versions of PowerPoint files.
This allows rendering PPTX files with original formatting in Speed Run mode.
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add pdf_content column to study_sessions table"""

    # Create engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        logger.info("=" * 70)
        logger.info("Migration: Add pdf_content field to study_sessions")
        logger.info("=" * 70)

        # Check if column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('study_sessions')]

        if 'pdf_content' in columns:
            logger.info("⚠️  Column 'pdf_content' already exists, skipping migration")
        else:
            logger.info("📋 Adding column 'pdf_content' to study_sessions table...")

            # Add the column using raw SQL (PostgreSQL)
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN pdf_content TEXT;"))
                conn.commit()

            logger.info("✅ Column added successfully")

        logger.info("\n" + "=" * 70)
        logger.info("Migration completed successfully")
        logger.info("=" * 70)
        logger.info("\nNote: Existing PPTX files will be converted to PDF when accessed in Speed Run mode")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
