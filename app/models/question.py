"""
Question database model.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base


class Question(Base):
    """Question model for quiz questions within topics."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # Array of 4 options
    correct_answer = Column(Integer, nullable=False)  # Index 0-3
    explanation = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)  # Order within topic
    source_text = Column(Text, nullable=True)  # Snippet of source material this question is based on
    source_page = Column(Integer, nullable=True)  # Page number in source document (for PDFs)

    # Relationships
    topic = relationship("Topic", back_populates="questions")

    def __repr__(self):
        return f"<Question(id={self.id}, topic_id={self.topic_id})>"
