"""
Topic database model.
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Float, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from app.database import Base
from app.models.study_session import GUID
from typing import Optional


class Topic(Base):
    """Topic model for organizing questions within study sessions."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    study_session_id = Column(GUID(), ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True, index=True)  # For hierarchical structure
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)  # Order in the session
    page_number = Column(Integer, nullable=True)  # Page/slide number in original document (1-indexed)
    is_category = Column(Boolean, default=False)  # True if this is a category/section, False if it's a leaf topic with questions
    completed = Column(Boolean, default=False)
    score = Column(Integer, nullable=True)  # Score as percentage 0-100
    current_question_index = Column(Integer, default=0)

    # Encrypted mentor narrative (data at rest)
    encrypted_mentor_narrative = Column(Text, nullable=True)  # Encrypted AI-generated mentor content

    # TODO: Encrypted TTS audio - pending database migration
    # encrypted_tts_audio = Column(Text, nullable=True)  # Encrypted base64 audio

    # DEPRECATED: Plain text mentor narrative (kept for backward compatibility during migration)
    # Will be removed after migration is complete
    mentor_narrative = Column(Text, nullable=True)

    # Workflow visualization fields (for skill-tree/progress tree UI)
    position_x = Column(Float, nullable=True)  # X coordinate in workflow visualization
    position_y = Column(Float, nullable=True)  # Y coordinate in workflow visualization
    workflow_stage = Column(String, default="locked")  # locked, quiz_available, quiz_completed, flashcard_review, completed

    # Prerequisite tracking (topics that must be completed before this one unlocks)
    prerequisite_topic_ids = Column(PG_ARRAY(Integer), nullable=True)  # Array of topic IDs

    # Relationships
    study_session = relationship("StudySession", back_populates="topics")
    parent_topic = relationship("Topic", remote_side=[id], backref="subtopics")
    questions = relationship("Question", back_populates="topic", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="topic", cascade="all, delete-orphan")

    def set_mentor_narrative(self, narrative: Optional[str]):
        """
        Set and encrypt mentor narrative

        Args:
            narrative: Plain text narrative to encrypt and store
        """
        from app.core.field_encryption import field_encryption

        if narrative:
            self.encrypted_mentor_narrative = field_encryption.encrypt(narrative)
            # Also set plain text for backward compatibility (temporary)
            self.mentor_narrative = narrative
        else:
            self.encrypted_mentor_narrative = None
            self.mentor_narrative = None

    def get_mentor_narrative(self) -> Optional[str]:
        """
        Get and decrypt mentor narrative

        Returns:
            Decrypted narrative text or None
        """
        from app.core.field_encryption import field_encryption

        # Try encrypted field first
        if self.encrypted_mentor_narrative:
            try:
                return field_encryption.decrypt(self.encrypted_mentor_narrative)
            except Exception as e:
                # Log error but fallback to plain text
                import logging
                logging.error(f"Failed to decrypt narrative for topic {self.id}: {e}")

        # Fallback to plain text (backward compatibility)
        return self.mentor_narrative

    # TODO: Uncomment when encrypted_tts_audio column is added to database
    # def set_tts_audio(self, audio_base64: Optional[str]):
    #     """
    #     Set and encrypt TTS audio (base64-encoded)
    #
    #     Args:
    #         audio_base64: Base64-encoded audio data to encrypt and store
    #     """
    #     from app.core.field_encryption import field_encryption
    #
    #     if audio_base64:
    #         self.encrypted_tts_audio = field_encryption.encrypt(audio_base64)
    #     else:
    #         self.encrypted_tts_audio = None
    #
    # def get_tts_audio(self) -> Optional[str]:
    #     """
    #     Get and decrypt TTS audio
    #
    #     Returns:
    #         Decrypted base64 audio data or None
    #     """
    #     from app.core.field_encryption import field_encryption
    #
    #     if self.encrypted_tts_audio:
    #         try:
    #             return field_encryption.decrypt(self.encrypted_tts_audio)
    #         except Exception as e:
    #             import logging
    #             logging.error(f"Failed to decrypt TTS audio for topic {self.id}: {e}")
    #             return None
    #
    #     return None

    def __repr__(self):
        return f"<Topic(id={self.id}, title={self.title}, session_id={self.study_session_id})>"
