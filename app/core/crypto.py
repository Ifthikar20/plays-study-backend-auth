"""
Cryptography Service

Handles all encryption/decryption for API communication.
Implements hybrid RSA + AES-256-GCM encryption:
- RSA-2048 for secure key exchange
- AES-256-GCM for fast payload encryption with authentication
- Nonce-based replay protection
- Request signing verification with HMAC-SHA256
"""

import base64
import hmac
import hashlib
import os
from typing import Tuple, Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
import logging

logger = logging.getLogger(__name__)

# RSA key size
RSA_KEY_SIZE = 2048
RSA_PUBLIC_EXPONENT = 65537

# AES key size (256 bits)
AES_KEY_SIZE = 32  # 256 bits / 8
AES_IV_SIZE = 12   # 96 bits for GCM
AES_TAG_SIZE = 16  # 128 bits


class CryptoService:
    """Handles encryption/decryption operations for the API"""

    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.key_version = "v1"
        self._initialize_keys()

    def _initialize_keys(self):
        """Initialize or load RSA key pair"""
        # Try to load from environment variable (production)
        private_key_pem = os.getenv("RSA_PRIVATE_KEY_PEM")

        if private_key_pem:
            logger.info("[Crypto] Loading RSA keys from environment")
            try:
                self.private_key = serialization.load_pem_private_key(
                    private_key_pem.encode(),
                    password=None,
                    backend=default_backend()
                )
                self.public_key = self.private_key.public_key()
                logger.info("[Crypto] ✅ RSA keys loaded from environment")
                return
            except Exception as e:
                logger.error(f"[Crypto] Failed to load keys from environment: {e}")

        # Generate new key pair (development)
        logger.info("[Crypto] Generating new RSA key pair...")
        self.private_key = rsa.generate_private_key(
            public_exponent=RSA_PUBLIC_EXPONENT,
            key_size=RSA_KEY_SIZE,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        logger.info("[Crypto] ✅ RSA key pair generated")

        # Log warning in production
        if os.getenv("ENVIRONMENT") == "production":
            logger.warning("[Crypto] ⚠️ Using generated keys in production! Set RSA_PRIVATE_KEY_PEM")

    def get_public_key_pem(self) -> str:
        """Get public key in PEM format for client"""
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')

    def get_key_version(self) -> str:
        """Get current key version for rotation support"""
        return self.key_version

    def decrypt_aes_key(self, encrypted_key_b64: str) -> bytes:
        """
        Decrypt AES key using RSA private key

        Args:
            encrypted_key_b64: Base64-encoded encrypted AES key

        Returns:
            Decrypted AES key bytes (32 bytes for AES-256)
        """
        try:
            encrypted_key = base64.b64decode(encrypted_key_b64)

            aes_key = self.private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            if len(aes_key) != AES_KEY_SIZE:
                raise ValueError(f"Invalid AES key size: {len(aes_key)} bytes")

            return aes_key

        except Exception as e:
            logger.error(f"[Crypto] AES key decryption failed: {e}")
            raise ValueError("Failed to decrypt AES key")

    def encrypt_aes_key(self, aes_key: bytes) -> str:
        """
        Encrypt AES key using RSA public key

        Args:
            aes_key: AES key bytes (32 bytes for AES-256)

        Returns:
            Base64-encoded encrypted AES key
        """
        try:
            if len(aes_key) != AES_KEY_SIZE:
                raise ValueError(f"Invalid AES key size: {len(aes_key)} bytes")

            encrypted_key = self.public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            return base64.b64encode(encrypted_key).decode('utf-8')

        except Exception as e:
            logger.error(f"[Crypto] AES key encryption failed: {e}")
            raise ValueError("Failed to encrypt AES key")

    def decrypt_payload(
        self,
        encrypted_data_b64: str,
        aes_key: bytes,
        iv_b64: str,
        auth_tag_b64: str
    ) -> Dict[str, Any]:
        """
        Decrypt payload using AES-256-GCM

        Args:
            encrypted_data_b64: Base64-encoded encrypted data
            aes_key: AES key bytes
            iv_b64: Base64-encoded initialization vector
            auth_tag_b64: Base64-encoded authentication tag

        Returns:
            Decrypted payload as dictionary
        """
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_data_b64)
            iv = base64.b64decode(iv_b64)
            auth_tag = base64.b64decode(auth_tag_b64)

            # Validate sizes
            if len(iv) != AES_IV_SIZE:
                raise ValueError(f"Invalid IV size: {len(iv)} bytes")
            if len(auth_tag) != AES_TAG_SIZE:
                raise ValueError(f"Invalid auth tag size: {len(auth_tag)} bytes")

            # Create cipher
            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.GCM(iv, auth_tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt
            plaintext = decryptor.update(encrypted_data) + decryptor.finalize()

            # Parse JSON
            import json
            payload = json.loads(plaintext.decode('utf-8'))

            return payload

        except InvalidTag:
            logger.error("[Crypto] Authentication tag verification failed")
            raise ValueError("Authentication failed - data may be tampered")
        except Exception as e:
            logger.error(f"[Crypto] Payload decryption failed: {e}")
            raise ValueError("Failed to decrypt payload")

    def encrypt_payload(
        self,
        data: Dict[str, Any],
        aes_key: bytes
    ) -> Dict[str, str]:
        """
        Encrypt payload using AES-256-GCM

        Args:
            data: Dictionary to encrypt
            aes_key: AES key bytes

        Returns:
            Dictionary with encrypted_data, iv, and auth_tag (all base64)
        """
        try:
            # Generate random IV
            iv = os.urandom(AES_IV_SIZE)

            # Convert to JSON
            import json
            plaintext = json.dumps(data).encode('utf-8')

            # Create cipher
            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Encrypt
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()

            # Get authentication tag
            auth_tag = encryptor.tag

            return {
                'encrypted_data': base64.b64encode(ciphertext).decode('utf-8'),
                'iv': base64.b64encode(iv).decode('utf-8'),
                'auth_tag': base64.b64encode(auth_tag).decode('utf-8')
            }

        except Exception as e:
            logger.error(f"[Crypto] Payload encryption failed: {e}")
            raise ValueError("Failed to encrypt payload")

    def generate_aes_key(self) -> bytes:
        """Generate a random AES-256 key"""
        return os.urandom(AES_KEY_SIZE)

    def verify_signature(
        self,
        method: str,
        url: str,
        timestamp: int,
        nonce: str,
        encrypted_data: str,
        signature_b64: str
    ) -> bool:
        """
        Verify HMAC-SHA256 signature of request

        Args:
            method: HTTP method (e.g., "POST")
            url: Request URL
            timestamp: Request timestamp
            nonce: Request nonce (used as HMAC key)
            encrypted_data: Encrypted payload (base64)
            signature_b64: Signature to verify (base64)

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Recreate the message
            message = f"{method}|{url}|{timestamp}|{nonce}|{encrypted_data}"

            # Compute HMAC using nonce as key
            computed_sig = hmac.new(
                nonce.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()

            # Decode provided signature
            provided_sig = base64.b64decode(signature_b64)

            # Constant-time comparison
            return hmac.compare_digest(computed_sig, provided_sig)

        except Exception as e:
            logger.error(f"[Crypto] Signature verification failed: {e}")
            return False

    def validate_timestamp(self, timestamp: int, max_age: int = 120) -> bool:
        """
        Validate request timestamp

        Args:
            timestamp: Request timestamp (Unix seconds)
            max_age: Maximum age in seconds (default: 120 = 2 minutes)

        Returns:
            True if timestamp is valid, False otherwise
        """
        import time
        now = int(time.time())
        age = now - timestamp

        if age < 0:
            logger.warning(f"[Crypto] Request timestamp is in the future: {timestamp}")
            return False

        if age > max_age:
            logger.warning(f"[Crypto] Request timestamp is too old: {age}s > {max_age}s")
            return False

        return True


# Global singleton instance
crypto_service = CryptoService()
