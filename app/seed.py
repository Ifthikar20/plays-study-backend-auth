"""
Database seeding script to populate initial data.
Run this after creating the database to add sample games.
"""
from app.database import SessionLocal, engine, Base
from app.models.game import Game
from app.models.user import User
from app.core.security import get_password_hash


def seed_database():
    """Seed the database with initial data."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if games already exist
        existing_games = db.query(Game).count()
        if existing_games > 0:
            print("Games already exist, skipping game seeding...")
        else:
            # Create sample games
            games = [
                Game(
                    title="Flash Cards",
                    description="Master topics with interactive flashcards",
                    image="https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?w=400&h=300&fit=crop",
                    category="Memory Games",
                    difficulty="Easy",
                    likes=1250,
                    rating=4.5,
                    estimated_time=15,
                    xp_reward=50,
                    is_active=True,
                ),
                Game(
                    title="Quick Quiz",
                    description="Test your knowledge with timed questions",
                    image="https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400&h=300&fit=crop",
                    category="Challenging & High XP",
                    difficulty="Medium",
                    likes=980,
                    rating=4.3,
                    estimated_time=10,
                    xp_reward=75,
                    is_active=True,
                ),
                Game(
                    title="Memory Match",
                    description="Match concepts to improve retention",
                    image="https://images.unsplash.com/photo-1611068813580-c0f163e885b5?w=400&h=300&fit=crop",
                    category="Memory Games",
                    difficulty="Easy",
                    likes=1580,
                    rating=4.8,
                    estimated_time=20,
                    xp_reward=100,
                    is_active=True,
                ),
                Game(
                    title="Speed Challenge",
                    description="Rapid-fire questions to boost your skills",
                    image="https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=400&h=300&fit=crop",
                    category="Challenging & High XP",
                    difficulty="Hard",
                    likes=2100,
                    rating=4.9,
                    estimated_time=5,
                    xp_reward=125,
                    is_active=True,
                ),
                Game(
                    title="Deep Dive",
                    description="In-depth exploration of complex topics",
                    image="https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=300&fit=crop",
                    category="Challenging & High XP",
                    difficulty="Hard",
                    likes=1750,
                    rating=4.6,
                    estimated_time=30,
                    xp_reward=200,
                    is_active=True,
                ),
                Game(
                    title="Practice Arena",
                    description="Apply your knowledge in realistic scenarios",
                    image="https://images.unsplash.com/photo-1551818255-e6e10975bc17?w=400&h=300&fit=crop",
                    category="Riddles",
                    difficulty="Medium",
                    likes=1320,
                    rating=4.4,
                    estimated_time=25,
                    xp_reward=150,
                    is_active=True,
                ),
                Game(
                    title="Platformer Adventure",
                    description="Jump through challenges to collect knowledge coins",
                    image="https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=400&h=300&fit=crop",
                    category="Memory Games",
                    difficulty="Medium",
                    likes=2300,
                    rating=4.7,
                    estimated_time=20,
                    xp_reward=180,
                    is_active=True,
                ),
            ]

            db.add_all(games)
            db.commit()
            print(f"✓ Seeded {len(games)} games successfully!")

        # Create a test user (optional)
        try:
            existing_user = db.query(User).filter(User.email == "test@example.com").first()
            if not existing_user:
                test_user = User(
                    email="test@example.com",
                    name="Test User",
                    hashed_password=get_password_hash("password123"),
                    xp=250,
                    level=3,
                    is_active=True,
                )
                db.add(test_user)
                db.commit()
                print("✓ Created test user: test@example.com / password123")
            else:
                print("Test user already exists, skipping...")
        except Exception as e:
            print(f"⚠️  Skipping test user creation (bcrypt error): {str(e)}")
            db.rollback()

        print("\n✅ Database seeding completed successfully!")

    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
