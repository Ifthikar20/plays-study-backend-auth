"""
Field-Level Encryption for Data at Rest

Uses Fernet (symmetric encryption) for encrypting sensitive database fields like:
- Mentor narratives
- User content
- Study session materials

Uses AES-128-CBC under the hood with HMAC-SHA256 for authentication.
"""

import os
import base64
import logging
from cryptography.fernet import Fernet, InvalidToken
from typing import Optional

logger = logging.getLogger(__name__)


class FieldEncryption:
    """Handles encryption/decryption of sensitive database fields"""

    def __init__(self):
        self.fernet = None
        self._initialize_key()

    def _initialize_key(self):
        """Initialize or load encryption key"""
        # Try to load from environment variable (production)
        encryption_key = os.getenv("FIELD_ENCRYPTION_KEY")

        if encryption_key:
            logger.info("[FieldEncryption] Loading encryption key from environment")
            try:
                # Validate and load the key
                self.fernet = Fernet(encryption_key.encode())
                logger.info("[FieldEncryption] ✅ Encryption key loaded")
                return
            except Exception as e:
                logger.error(f"[FieldEncryption] Failed to load key from environment: {e}")
                raise ValueError("Invalid encryption key in environment")

        # Generate new key (development only)
        if os.getenv("ENVIRONMENT") != "production":
            logger.warning("[FieldEncryption] ⚠️ Generating new encryption key (DEVELOPMENT ONLY)")
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
            logger.info(f"[FieldEncryption] Generated key: {key.decode()}")
            logger.info("[FieldEncryption] Add this to .env: FIELD_ENCRYPTION_KEY=" + key.decode())
        else:
            raise ValueError("FIELD_ENCRYPTION_KEY must be set in production")

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypt a string field

        Args:
            plaintext: The text to encrypt (or None)

        Returns:
            Base64-encoded encrypted data (or None if input was None)
        """
        if plaintext is None or plaintext == "":
            return None

        try:
            # Encrypt the text
            encrypted = self.fernet.encrypt(plaintext.encode('utf-8'))

            # Return as base64 string for database storage
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"[FieldEncryption] Encryption error: {e}")
            raise

    def decrypt(self, encrypted_text: Optional[str]) -> Optional[str]:
        """
        Decrypt an encrypted field

        Args:
            encrypted_text: Base64-encoded encrypted data (or None)

        Returns:
            Decrypted plaintext (or None if input was None)
        """
        if encrypted_text is None or encrypted_text == "":
            return None

        try:
            # Decrypt the data
            decrypted = self.fernet.decrypt(encrypted_text.encode('utf-8'))

            # Return as string
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("[FieldEncryption] Invalid token - data may be corrupted or key mismatch")
            raise ValueError("Failed to decrypt data - invalid encryption key")
        except Exception as e:
            logger.error(f"[FieldEncryption] Decryption error: {e}")
            raise

    def is_encrypted(self, text: Optional[str]) -> bool:
        """
        Check if a field appears to be encrypted

        Args:
            text: The text to check

        Returns:
            True if the text looks like encrypted data
        """
        if not text:
            return False

        # Fernet tokens start with 'gAAAAA' when base64 encoded
        # This is a heuristic check
        try:
            return text.startswith('gAAAAA')
        except:
            return False


# Global instance
field_encryption = FieldEncryption()
