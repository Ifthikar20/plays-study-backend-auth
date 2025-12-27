"""
Flashcard database model for spaced repetition learning.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.database import Base


class Flashcard(Base):
    """
    Flashcard model for post-topic review using spaced repetition.

    This is a SEPARATE workflow node from quiz questions.
    Users complete quizzes first, then review flashcards to reinforce learning.
    """

    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Flashcard content
    front = Column(Text, nullable=False)  # Question/term
    back = Column(Text, nullable=False)   # Answer/definition
    hint = Column(Text, nullable=True)    # Optional hint
    order_index = Column(Integer, nullable=False, default=0)

    # Spaced repetition fields (SM-2 algorithm)
    ease_factor = Column(Float, default=2.5)  # How "easy" this card is (2.5 is default)
    interval_days = Column(Integer, default=1)  # Days until next review
    repetitions = Column(Integer, default=0)  # Number of successful reviews
    next_review_date = Column(DateTime, nullable=True)  # When to review next
    last_reviewed_at = Column(DateTime, nullable=True)  # Last review timestamp

    # Review statistics
    total_reviews = Column(Integer, default=0)  # Total times reviewed
    correct_reviews = Column(Integer, default=0)  # Number of correct reviews

    # Relationships
    topic = relationship("Topic", back_populates="flashcards")

    def calculate_next_review(self, quality: int):
        """
        Calculate next review date using SM-2 spaced repetition algorithm.

        Args:
            quality: Rating from 0-5
                0-2: Failed (need to review again soon)
                3: Difficult (passed but hard)
                4: Good (passed with some effort)
                5: Easy (passed easily)

        Reference: https://en.wikipedia.org/wiki/SuperMemo#SM-2_algorithm
        """
        self.total_reviews += 1
        self.last_reviewed_at = datetime.utcnow()

        # Update ease factor
        if quality >= 3:
            self.correct_reviews += 1
            self.repetitions += 1
            self.ease_factor = max(1.3, self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        else:
            # Failed - reset repetitions
            self.repetitions = 0
            self.interval_days = 1

        # Calculate interval
        if self.repetitions == 0:
            self.interval_days = 1
        elif self.repetitions == 1:
            self.interval_days = 6
        else:
            self.interval_days = int(self.interval_days * self.ease_factor)

        # Set next review date
        self.next_review_date = datetime.utcnow() + timedelta(days=self.interval_days)

    def is_due_for_review(self) -> bool:
        """Check if this flashcard is due for review."""
        if self.next_review_date is None:
            return True  # Never reviewed
        return datetime.utcnow() >= self.next_review_date

    def get_accuracy(self) -> float:
        """Get accuracy percentage for this flashcard."""
        if self.total_reviews == 0:
            return 0.0
        return (self.correct_reviews / self.total_reviews) * 100

    def __repr__(self):
        return f"<Flashcard(id={self.id}, topic_id={self.topic_id}, front={self.front[:30]}...)>"
