"""
Text-to-Speech Service
Handles TTS generation with caching and provider management
"""
import hashlib
import redis
from typing import Optional, Dict, List
from app.services.tts_providers import TTSProviderFactory, TTSProvider
from app.config import settings
import json


class TTSService:
    """Service for managing TTS generation with caching."""

    def __init__(self):
        # Use a separate Redis client for binary data (no decode_responses)
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)
        except Exception as e:
            print(f"Warning: Redis not available for TTS caching: {e}")
            self.redis_client = None
        self.cache_ttl = 3600 * 24  # 24 hours cache for audio

    def _generate_cache_key(self, provider: str, text: str, voice: str, **kwargs) -> str:
        """Generate cache key for TTS request."""
        # Create a deterministic hash of the request
        params = {
            "provider": provider,
            "text": text,
            "voice": voice,
            **kwargs
        }
        params_str = json.dumps(params, sort_keys=True)
        hash_key = hashlib.sha256(params_str.encode()).hexdigest()
        return f"tts:audio:{hash_key}"

    async def generate_speech(
        self,
        text: str,
        provider_name: str = "openai",
        voice: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Generate speech audio from text.

        Args:
            text: Text to convert to speech
            provider_name: TTS provider to use ('openai' or 'google-cloud')
            voice: Voice ID to use (provider-specific)
            **kwargs: Additional provider-specific parameters

        Returns:
            Audio data as bytes (MP3 format)
        """
        # Get provider
        provider = TTSProviderFactory.get_provider(provider_name)

        # Set default voice if not provided
        if not voice:
            voices = provider.get_available_voices()
            voice = voices[0]["id"] if voices else "alloy"

        # Check cache first
        cache_key = self._generate_cache_key(provider_name, text, voice, **kwargs)
        try:
            if self.redis_client:
                cached_audio = self.redis_client.get(cache_key)
                if cached_audio:
                    return cached_audio  # Binary data as bytes
        except Exception:
            # Cache miss or error - continue to generate
            pass

        # Generate audio
        audio_data = await provider.generate_speech(text, voice, **kwargs)

        # Cache the result (binary data)
        try:
            if self.redis_client:
                self.redis_client.setex(cache_key, self.cache_ttl, audio_data)
        except Exception:
            # Cache write failed - continue without caching
            pass

        return audio_data

    def get_available_providers(self) -> List[Dict[str, any]]:
        """Get list of available TTS providers."""
        return TTSProviderFactory.get_available_providers()

    def get_provider_voices(self, provider_name: str) -> List[Dict[str, str]]:
        """Get available voices for a specific provider."""
        provider = TTSProviderFactory.get_provider(provider_name)
        return provider.get_available_voices()

    def get_all_voices(self) -> Dict[str, List[Dict[str, str]]]:
        """Get all available voices grouped by provider."""
        voices = {}
        for provider_info in self.get_available_providers():
            if provider_info["configured"]:
                provider_name = provider_info["id"]
                voices[provider_name] = self.get_provider_voices(provider_name)
        return voices


# Singleton instance
tts_service = TTSService()
