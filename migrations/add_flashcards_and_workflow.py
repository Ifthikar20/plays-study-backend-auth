"""
Migration: Add flashcards table and workflow visualization fields

Adds:
1. flashcards table with spaced repetition support
2. Workflow visualization fields to topics (position_x, position_y, workflow_stage)
3. Prerequisite tracking (prerequisite_topic_ids)
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, Text, create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add flashcards table and workflow fields to topics"""

    # Create engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        logger.info("=" * 70)
        logger.info("Migration: Add flashcards and workflow visualization")
        logger.info("=" * 70)

        from sqlalchemy import inspect
        inspector = inspect(engine)

        # ===== PART 1: Create flashcards table =====
        logger.info("\n📋 Creating flashcards table...")

        tables = inspector.get_table_names()
        if 'flashcards' in tables:
            logger.info("⚠️  Table 'flashcards' already exists, skipping creation")
        else:
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE flashcards (
                        id SERIAL PRIMARY KEY,
                        topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                        front TEXT NOT NULL,
                        back TEXT NOT NULL,
                        hint TEXT,
                        order_index INTEGER NOT NULL DEFAULT 0,
                        ease_factor FLOAT DEFAULT 2.5,
                        interval_days INTEGER DEFAULT 1,
                        repetitions INTEGER DEFAULT 0,
                        next_review_date TIMESTAMP,
                        last_reviewed_at TIMESTAMP,
                        total_reviews INTEGER DEFAULT 0,
                        correct_reviews INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                conn.commit()

            # Create index on topic_id for faster lookups
            with engine.connect() as conn:
                conn.execute(text("CREATE INDEX idx_flashcards_topic_id ON flashcards(topic_id);"))
                conn.commit()

            logger.info("✅ Table 'flashcards' created successfully")

        # ===== PART 2: Add workflow fields to topics table =====
        logger.info("\n📋 Adding workflow visualization fields to topics...")

        columns = [col['name'] for col in inspector.get_columns('topics')]

        fields_to_add = [
            ("position_x", "FLOAT"),
            ("position_y", "FLOAT"),
            ("workflow_stage", "VARCHAR DEFAULT 'locked'"),
            ("prerequisite_topic_ids", "INTEGER[]")  # PostgreSQL array
        ]

        for field_name, field_type in fields_to_add:
            if field_name in columns:
                logger.info(f"⚠️  Column '{field_name}' already exists, skipping")
            else:
                logger.info(f"  Adding column '{field_name}'...")
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE topics ADD COLUMN {field_name} {field_type};"))
                    conn.commit()
                logger.info(f"✅ Column '{field_name}' added")

        # ===== PART 3: Initialize workflow_stage for existing topics =====
        logger.info("\n📊 Initializing workflow_stage for existing topics...")

        with engine.connect() as conn:
            # Set first topic as quiz_available, rest as locked
            result = conn.execute(text("""
                UPDATE topics
                SET workflow_stage = CASE
                    WHEN order_index = 0 AND parent_topic_id IS NULL THEN 'quiz_available'
                    ELSE 'locked'
                END
                WHERE workflow_stage IS NULL OR workflow_stage = 'locked';
            """))
            conn.commit()
            logger.info(f"✅ Initialized workflow_stage for {result.rowcount} topics")

        # ===== VERIFICATION =====
        logger.info("\n🔍 Verifying migration...")

        # Check flashcards table
        if 'flashcards' in inspector.get_table_names():
            logger.info("✅ Table 'flashcards' exists")
        else:
            logger.error("❌ Table 'flashcards' not found!")

        # Check topics columns
        topic_columns = [col['name'] for col in inspector.get_columns('topics')]
        required_fields = ['position_x', 'position_y', 'workflow_stage', 'prerequisite_topic_ids']

        for field in required_fields:
            if field in topic_columns:
                logger.info(f"✅ Column 'topics.{field}' exists")
            else:
                logger.error(f"❌ Column 'topics.{field}' not found!")

        # Count topics by workflow_stage
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT workflow_stage, COUNT(*) as count
                FROM topics
                GROUP BY workflow_stage;
            """))
            logger.info("\n📊 Topic workflow stages:")
            for row in result:
                logger.info(f"  {row[0]}: {row[1]} topics")

        logger.info("\n" + "=" * 70)
        logger.info("Migration completed successfully")
        logger.info("=" * 70)

        logger.info("\n📚 Next Steps:")
        logger.info("  1. Update AI prompts to generate flashcards alongside questions")
        logger.info("  2. Create flashcard API endpoints")
        logger.info("  3. Add workflow visualization endpoint")
        logger.info("  4. Update frontend to display skill-tree UI")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
