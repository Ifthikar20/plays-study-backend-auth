"""
Migration: Add encrypted_mentor_narrative field to topics table

Adds encryption at rest for mentor narratives.
Migrates existing plain text narratives to encrypted format.
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, Text, create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.topic import Topic
from app.core.field_encryption import field_encryption
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add encrypted_mentor_narrative column and migrate existing data"""

    # Create engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        logger.info("=" * 70)
        logger.info("Migration: Add encrypted_mentor_narrative field")
        logger.info("=" * 70)

        # Check if column exists
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('topics')]

        if 'encrypted_mentor_narrative' in columns:
            logger.info("⚠️  Column 'encrypted_mentor_narrative' already exists, checking data migration...")
        else:
            logger.info("📋 Adding column 'encrypted_mentor_narrative' to topics table...")

            # Add the column using raw SQL (PostgreSQL)
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE topics ADD COLUMN encrypted_mentor_narrative TEXT;"))
                conn.commit()

            logger.info("✅ Column added successfully")

        # Migrate existing plain text narratives to encrypted format
        logger.info("\n📊 Migrating existing narratives to encrypted format...")

        topics_with_narratives = db.query(Topic).filter(
            Topic.mentor_narrative.isnot(None),
            Topic.encrypted_mentor_narrative.is_(None)
        ).all()

        if not topics_with_narratives:
            logger.info("ℹ️  No plain text narratives found to migrate")
        else:
            logger.info(f"Found {len(topics_with_narratives)} topics with plain text narratives")

            migrated = 0
            failed = 0

            for topic in topics_with_narratives:
                try:
                    # Encrypt the narrative
                    encrypted = field_encryption.encrypt(topic.mentor_narrative)
                    topic.encrypted_mentor_narrative = encrypted

                    migrated += 1

                    if migrated % 10 == 0:
                        logger.info(f"  Migrated {migrated}/{len(topics_with_narratives)} narratives...")

                except Exception as e:
                    logger.error(f"❌ Failed to encrypt narrative for topic {topic.id}: {e}")
                    failed += 1

            # Commit all changes
            db.commit()

            logger.info(f"\n✅ Migration complete:")
            logger.info(f"  - Successfully migrated: {migrated}")
            logger.info(f"  - Failed: {failed}")

        # Verify encryption
        logger.info("\n🔍 Verifying encryption...")
        encrypted_count = db.query(Topic).filter(
            Topic.encrypted_mentor_narrative.isnot(None)
        ).count()

        plain_count = db.query(Topic).filter(
            Topic.mentor_narrative.isnot(None),
            Topic.encrypted_mentor_narrative.is_(None)
        ).count()

        logger.info(f"  - Topics with encrypted narratives: {encrypted_count}")
        logger.info(f"  - Topics with unencrypted narratives: {plain_count}")

        if plain_count > 0:
            logger.warning(f"⚠️  {plain_count} topics still have unencrypted narratives!")
        else:
            logger.info("✅ All narratives are encrypted")

        logger.info("\n" + "=" * 70)
        logger.info("Migration completed successfully")
        logger.info("=" * 70)

        # Test decryption on one topic
        if encrypted_count > 0:
            logger.info("\n🧪 Testing decryption on a sample topic...")
            sample_topic = db.query(Topic).filter(
                Topic.encrypted_mentor_narrative.isnot(None)
            ).first()

            if sample_topic:
                try:
                    decrypted = sample_topic.get_mentor_narrative()
                    if decrypted and len(decrypted) > 0:
                        logger.info(f"✅ Decryption test passed (topic {sample_topic.id})")
                        logger.info(f"  Preview: {decrypted[:100]}...")
                    else:
                        logger.error("❌ Decryption test failed - empty result")
                except Exception as e:
                    logger.error(f"❌ Decryption test failed: {e}")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
