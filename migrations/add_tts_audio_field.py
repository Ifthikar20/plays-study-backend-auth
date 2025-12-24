"""
Migration script to add encrypted_tts_audio column to topics table.
"""
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings

def run_migration():
    """Add encrypted_tts_audio column to topics table."""
    engine = create_engine(settings.DATABASE_URL)

    print("Starting migration: add_tts_audio_field")
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")

    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='topics' AND column_name='encrypted_tts_audio';
            """))

            if result.fetchone():
                print("✓ Column 'encrypted_tts_audio' already exists, skipping")
                return

            # Add the new column
            print("Adding column 'encrypted_tts_audio' to topics table...")
            conn.execute(text("ALTER TABLE topics ADD COLUMN encrypted_tts_audio TEXT;"))
            conn.commit()
            print("✓ Successfully added encrypted_tts_audio column")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        engine.dispose()

    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
