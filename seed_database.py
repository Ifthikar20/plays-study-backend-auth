"""
Database seeding script to populate with sample data.
"""
import sys
from pathlib import Path
import os

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Check if we should use SQLite for development
USE_SQLITE = os.getenv('USE_SQLITE', 'false').lower() == 'true'

if USE_SQLITE:
    print("🔄 Using SQLite for development...")
    # Temporarily override DATABASE_URL for SQLite
    os.environ['DATABASE_URL'] = 'sqlite:///./playstudy_dev.db'

from app.database import SessionLocal, engine
from app.models.user import User
from app.models.game import Game
from app.models.study_session import StudySession
from datetime import datetime, timedelta
import random
from passlib.context import CryptContext

# Create a simple password context for seeding
# Handle bcrypt version issues gracefully
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash_safe(password: str) -> str:
    """Safe password hashing with fallback."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Warning: bcrypt error ({e}), using simpler hash")
        # Fallback to simple hash for development
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


def seed_database():
    """Populate database with sample data."""

    # Test database connection first
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"\n❌ Database connection failed!")
        print(f"Error: {str(e)}")
        print("\n💡 To fix this issue:")
        print("   1. Make sure PostgreSQL is running:")
        print("      - macOS: brew services start postgresql")
        print("      - Linux: sudo systemctl start postgresql")
        print("      - Windows: Start PostgreSQL service")
        print("\n   2. Or use SQLite for development:")
        print("      USE_SQLITE=true python backend/seed_database.py")
        print("\n   3. Create the database if it doesn't exist:")
        print("      createdb playstudy_db")
        return

    # Create tables if using SQLite
    if USE_SQLITE:
        print("📦 Creating database tables...")
        from app.models.user import Base
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("🌱 Starting database seeding...")

        # Clear existing data (optional - comment out if you want to keep existing data)
        print("Clearing existing data...")
        db.query(StudySession).delete()
        db.query(Game).delete()
        db.query(User).delete()
        db.commit()

        # Create sample users
        print("Creating sample users...")
        users = [
            User(
                email="student@playstudy.ai",
                name="Student User",
                hashed_password=get_password_hash_safe("password123"),
                xp=2450,
                level=12,
                is_active=True,
            ),
            User(
                email="demo@playstudy.ai",
                name="Demo User",
                hashed_password=get_password_hash_safe("demo123"),
                xp=1200,
                level=8,
                is_active=True,
            ),
        ]

        for user in users:
            db.add(user)

        db.commit()
        print(f"✅ Created {len(users)} users")

        # Create sample games
        print("Creating sample games...")
        games_data = [
            {
                "title": "Math Speed Challenge",
                "description": "Race against time solving arithmetic and algebra problems. Perfect for sharpening mental math skills!",
                "category": "Mathematics",
                "image": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=400&h=300&fit=crop",
                "difficulty": "Medium",
                "likes": 1240,
                "rating": 4.8,
                "estimated_time": 15,
                "xp_reward": 150,
            },
            {
                "title": "Science Quiz Battle",
                "description": "Test your knowledge across physics, chemistry, and biology in this competitive quiz format.",
                "category": "Science",
                "image": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=400&h=300&fit=crop",
                "difficulty": "Hard",
                "likes": 980,
                "rating": 4.6,
                "estimated_time": 20,
                "xp_reward": 200,
            },
            {
                "title": "History Trivia Rush",
                "description": "Journey through time answering questions about world events, famous figures, and ancient civilizations.",
                "category": "History",
                "image": "https://images.unsplash.com/photo-1461360370896-922624d12a74?w=400&h=300&fit=crop",
                "difficulty": "Easy",
                "likes": 756,
                "rating": 4.5,
                "estimated_time": 10,
                "xp_reward": 100,
            },
            {
                "title": "Language Master",
                "description": "Build vocabulary and grammar skills across multiple languages with interactive challenges.",
                "category": "Languages",
                "image": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400&h=300&fit=crop",
                "difficulty": "Medium",
                "likes": 1100,
                "rating": 4.9,
                "estimated_time": 12,
                "xp_reward": 120,
            },
            {
                "title": "Geography Explorer",
                "description": "Explore countries, capitals, and landmarks. Learn about world geography through fun quizzes!",
                "category": "Geography",
                "image": "https://images.unsplash.com/photo-1524661135-423995f22d0b?w=400&h=300&fit=crop",
                "difficulty": "Easy",
                "likes": 620,
                "rating": 4.4,
                "estimated_time": 10,
                "xp_reward": 100,
            },
            {
                "title": "Coding Challenge",
                "description": "Solve programming puzzles and debug code snippets. Great for aspiring developers!",
                "category": "Programming",
                "image": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=400&h=300&fit=crop",
                "difficulty": "Hard",
                "likes": 890,
                "rating": 4.7,
                "estimated_time": 25,
                "xp_reward": 250,
            },
            {
                "title": "Bean Platformer Adventure",
                "description": "Classic platformer game! Jump on enemies, collect coins, and reach the portal. 2 levels of challenging fun!",
                "category": "Programming",
                "image": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=400&h=300&fit=crop",
                "difficulty": "Medium",
                "likes": 1450,
                "rating": 4.9,
                "estimated_time": 15,
                "xp_reward": 180,
            },
            {
                "title": "Memory Card Match",
                "description": "Classic memory matching game! Flip cards to find pairs and train your memory skills.",
                "category": "Memory Games",
                "image": "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=400&h=300&fit=crop",
                "difficulty": "Easy",
                "likes": 1350,
                "rating": 4.7,
                "estimated_time": 8,
                "xp_reward": 80,
            },
            {
                "title": "Pattern Recognition",
                "description": "Identify and complete complex patterns. Perfect for developing analytical thinking!",
                "category": "Memory Games",
                "image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=400&h=300&fit=crop",
                "difficulty": "Medium",
                "likes": 920,
                "rating": 4.6,
                "estimated_time": 12,
                "xp_reward": 140,
            },
            {
                "title": "Sequence Master",
                "description": "Remember and repeat increasingly complex sequences. Test your short-term memory!",
                "category": "Memory Games",
                "image": "https://images.unsplash.com/photo-1516534775068-ba3e7458af70?w=400&h=300&fit=crop",
                "difficulty": "Hard",
                "likes": 780,
                "rating": 4.8,
                "estimated_time": 15,
                "xp_reward": 200,
            },
            {
                "title": "Brain Teaser Arena",
                "description": "Solve mind-bending puzzles that will push your problem-solving skills to the limit!",
                "category": "Challenging & High XP",
                "image": "https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?w=400&h=300&fit=crop",
                "difficulty": "Hard",
                "likes": 1580,
                "rating": 4.9,
                "estimated_time": 30,
                "xp_reward": 350,
            },
            {
                "title": "Logic Maze Challenge",
                "description": "Navigate through complex logic puzzles and mazes. High rewards for the brave!",
                "category": "Challenging & High XP",
                "image": "https://images.unsplash.com/photo-1515524738708-327f6b0037a7?w=400&h=300&fit=crop",
                "difficulty": "Hard",
                "likes": 1420,
                "rating": 4.7,
                "estimated_time": 25,
                "xp_reward": 300,
            },
            {
                "title": "Ultimate Quiz Master",
                "description": "The toughest quiz you'll ever face! Answer 100 questions for massive XP rewards.",
                "category": "Challenging & High XP",
                "image": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400&h=300&fit=crop",
                "difficulty": "Hard",
                "likes": 1890,
                "rating": 4.8,
                "estimated_time": 35,
                "xp_reward": 400,
            },
            {
                "title": "Mystery Riddle Box",
                "description": "Unlock the box by solving clever riddles and lateral thinking puzzles!",
                "category": "Riddles",
                "image": "https://images.unsplash.com/photo-1533158326339-7f3cf2404354?w=400&h=300&fit=crop",
                "difficulty": "Medium",
                "likes": 1120,
                "rating": 4.6,
                "estimated_time": 18,
                "xp_reward": 160,
            },
            {
                "title": "Wordplay Workshop",
                "description": "Solve word riddles, anagrams, and linguistic puzzles. Fun with language!",
                "category": "Riddles",
                "image": "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=400&h=300&fit=crop",
                "difficulty": "Easy",
                "likes": 850,
                "rating": 4.5,
                "estimated_time": 12,
                "xp_reward": 110,
            },
            {
                "title": "Detective's Dilemma",
                "description": "Use deduction and logic to solve mystery riddles like a true detective!",
                "category": "Riddles",
                "image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=400&h=300&fit=crop",
                "difficulty": "Hard",
                "likes": 1240,
                "rating": 4.9,
                "estimated_time": 22,
                "xp_reward": 220,
            },
            {
                "title": "Picture Perfect Riddles",
                "description": "Visual riddles that require you to think outside the box. Can you crack them all?",
                "category": "Riddles",
                "image": "https://images.unsplash.com/photo-1618761714954-0b8cd0026356?w=400&h=300&fit=crop",
                "difficulty": "Medium",
                "likes": 980,
                "rating": 4.7,
                "estimated_time": 15,
                "xp_reward": 170,
            },
        ]

        games = []
        for game_data in games_data:
            game = Game(**game_data)
            db.add(game)
            games.append(game)

        db.commit()
        print(f"✅ Created {len(games)} games")

        # Create sample study sessions for first user
        print("Creating sample study sessions...")
        first_user = users[0]

        sessions_data = [
            {
                "title": "Calculus Fundamentals",
                "topic": "Calculus",
                "duration": 7200,  # 2 hours in seconds
                "progress": 92,
                "topics_count": 12,
                "accuracy": 88,
                "xp_earned": 200,
                "has_full_study": True,
                "has_speed_run": True,
                "has_quiz": True,
                "created_at": datetime.utcnow() - timedelta(hours=2),
            },
            {
                "title": "Organic Chemistry",
                "topic": "Chemistry",
                "duration": 5400,  # 1.5 hours
                "progress": 85,
                "topics_count": 8,
                "accuracy": 82,
                "xp_earned": 150,
                "has_full_study": False,
                "has_speed_run": True,
                "has_quiz": False,
                "created_at": datetime.utcnow() - timedelta(hours=5),
            },
            {
                "title": "World War II History",
                "topic": "History",
                "duration": 6300,  # 1.75 hours
                "progress": 78,
                "topics_count": 15,
                "accuracy": 90,
                "xp_earned": 180,
                "has_full_study": True,
                "has_speed_run": False,
                "has_quiz": True,
                "created_at": datetime.utcnow() - timedelta(days=1),
            },
            {
                "title": "Spanish Vocabulary",
                "topic": "Languages",
                "duration": 3600,  # 1 hour
                "progress": 95,
                "topics_count": 20,
                "accuracy": 94,
                "xp_earned": 220,
                "has_full_study": True,
                "has_speed_run": True,
                "has_quiz": True,
                "created_at": datetime.utcnow() - timedelta(days=1),
            },
            {
                "title": "Geography Capitals",
                "topic": "Geography",
                "duration": 4800,  # 1.33 hours
                "progress": 88,
                "topics_count": 10,
                "accuracy": 85,
                "xp_earned": 140,
                "has_full_study": False,
                "has_speed_run": False,
                "has_quiz": True,
                "created_at": datetime.utcnow() - timedelta(days=2),
            },
            {
                "title": "Python Basics",
                "topic": "Programming",
                "duration": 9000,  # 2.5 hours
                "progress": 91,
                "topics_count": 14,
                "accuracy": 87,
                "xp_earned": 210,
                "has_full_study": True,
                "has_speed_run": True,
                "has_quiz": False,
                "created_at": datetime.utcnow() - timedelta(days=2),
            },
        ]

        sessions = []
        for session_data in sessions_data:
            session = StudySession(
                user_id=first_user.id,
                game_id=random.choice(games).id if games else None,
                status="completed",
                is_completed=True,
                **session_data
            )
            db.add(session)
            sessions.append(session)

        db.commit()
        print(f"✅ Created {len(sessions)} study sessions")

        print("\n🎉 Database seeding completed successfully!")
        print("\n📊 Summary:")
        print(f"  Users: {len(users)}")
        print(f"  Games: {len(games)}")
        print(f"  Study Sessions: {len(sessions)}")
        print("\n👤 Test accounts:")
        print("  Email: student@playstudy.ai | Password: password123")
        print("  Email: demo@playstudy.ai | Password: demo123")

    except Exception as e:
        print(f"\n❌ Error seeding database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
