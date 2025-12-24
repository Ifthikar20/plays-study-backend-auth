"""
Text-to-Speech Provider Implementation
Handles TTS generation using OpenAI and Google Cloud Text-to-Speech APIs
"""
import base64
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    async def generate_speech(
        self, text: str, voice: str, **kwargs
    ) -> bytes:
        """Generate speech audio from text."""
        pass

    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class OpenAITTSProvider(TTSProvider):
    """OpenAI Text-to-Speech provider."""

    def __init__(self):
        print("\n🔊 [OpenAITTSProvider] Initializing...")
        self.api_key = getattr(settings, "OPENAI_API_KEY", None)
        self.base_url = "https://api.openai.com/v1/audio/speech"

        # Enhanced logging
        key_present = bool(self.api_key)
        key_length = len(self.api_key) if self.api_key else 0

        print(f"🔊 [OpenAITTSProvider] API Key Present: {key_present}")
        print(f"🔊 [OpenAITTSProvider] Key Length: {key_length}")

        logger.info(f"[OpenAI TTS] Initializing provider")
        logger.info(f"[OpenAI TTS] API Key Present: {key_present}")
        logger.info(f"[OpenAI TTS] Key Length: {key_length}")

        if self.api_key:
            print(f"✅ [OpenAITTSProvider] Configured with key: {self.api_key[:7]}...{self.api_key[-4:]}")
            logger.info(f"[OpenAI TTS] API Key (first 7 chars): {self.api_key[:7]}...")
        else:
            print(f"❌ [OpenAITTSProvider] No API key found")
            logger.warning(f"[OpenAI TTS] No API key found")

    def is_configured(self) -> bool:
        configured = bool(self.api_key)
        print(f"🔊 [OpenAITTSProvider] is_configured() called: {configured}")
        logger.info(f"[OpenAI TTS] is_configured() = {configured}")
        return configured

    async def generate_speech(
        self,
        text: str,
        voice: str = "alloy",
        speed: float = 1.0,
        model: str = "tts-1",
        **kwargs
    ) -> bytes:
        """Generate speech using OpenAI TTS API."""
        if not self.is_configured():
            raise ValueError("OpenAI API key not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": text,
                    "voice": voice,
                    "speed": speed,
                },
            )

            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"OpenAI TTS API error: {error_detail}")

            return response.content

    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get OpenAI TTS voices."""
        return [
            {"id": "alloy", "name": "Alloy", "description": "Neutral and balanced", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "description": "Male, clear and direct", "gender": "male"},
            {"id": "fable", "name": "Fable", "description": "British accent, expressive", "gender": "male"},
            {"id": "onyx", "name": "Onyx", "description": "Deep and authoritative", "gender": "male"},
            {"id": "nova", "name": "Nova", "description": "Female, energetic and friendly", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "description": "Female, warm and soothing", "gender": "female"},
        ]


class GoogleCloudTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech provider."""

    def __init__(self):
        print("\n🔊 [GoogleCloudTTSProvider] Initializing...")
        self.api_key = getattr(settings, "GOOGLE_CLOUD_API_KEY", None)
        self.base_url = "https://texttospeech.googleapis.com/v1/text:synthesize"

        # Enhanced logging
        key_present = bool(self.api_key)
        is_placeholder = self.api_key == "your-google-cloud-api-key-here" if self.api_key else False
        key_length = len(self.api_key) if self.api_key else 0

        print(f"🔊 [GoogleCloudTTSProvider] API Key Present: {key_present}")
        print(f"🔊 [GoogleCloudTTSProvider] Key Length: {key_length}")
        print(f"🔊 [GoogleCloudTTSProvider] Is Placeholder: {is_placeholder}")

        logger.info(f"[Google Cloud TTS] Initializing provider")
        logger.info(f"[Google Cloud TTS] API Key Present: {key_present}")
        logger.info(f"[Google Cloud TTS] Key Length: {key_length}")
        logger.info(f"[Google Cloud TTS] Is Placeholder: {is_placeholder}")

        if self.api_key and not is_placeholder:
            print(f"✅ [GoogleCloudTTSProvider] Configured with key: {self.api_key[:15]}...{self.api_key[-8:]}")
            logger.info(f"[Google Cloud TTS] API Key (first 15 chars): {self.api_key[:15]}...")
            logger.info(f"[Google Cloud TTS] API Key (last 8 chars): ...{self.api_key[-8:]}")
        elif is_placeholder:
            print(f"❌ [GoogleCloudTTSProvider] Placeholder key detected - NOT CONFIGURED")
            logger.warning(f"[Google Cloud TTS] Placeholder key detected")
        else:
            print(f"❌ [GoogleCloudTTSProvider] No API key found")
            logger.warning(f"[Google Cloud TTS] No API key found")

    def is_configured(self) -> bool:
        # Check for actual configuration (not placeholder)
        has_key = bool(self.api_key)
        is_placeholder = self.api_key == "your-google-cloud-api-key-here" if self.api_key else False
        configured = has_key and not is_placeholder

        print(f"🔊 [GoogleCloudTTSProvider] is_configured() called")
        print(f"   - Has Key: {has_key}")
        print(f"   - Is Placeholder: {is_placeholder}")
        print(f"   - Result: {configured}")

        logger.info(f"[Google Cloud TTS] is_configured() = {configured} (has_key={has_key}, is_placeholder={is_placeholder})")
        return configured

    async def generate_speech(
        self,
        text: str,
        voice: str = "en-US-Neural2-F",
        speed: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        **kwargs
    ) -> bytes:
        """Generate speech using Google Cloud TTS API."""
        if not self.is_configured():
            raise ValueError("Google Cloud API key not configured")

        # Extract language code from voice name
        language_code = "-".join(voice.split("-")[:2])

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "input": {"text": text},
                    "voice": {
                        "languageCode": language_code,
                        "name": voice,
                    },
                    "audioConfig": {
                        "audioEncoding": "MP3",
                        "speakingRate": speed,
                        "pitch": pitch,
                        "volumeGainDb": volume_gain_db,
                    },
                },
            )

            if response.status_code != 200:
                error_detail = response.json() if response.content else response.text
                raise Exception(f"Google Cloud TTS API error: {error_detail}")

            # Google returns base64 encoded audio
            data = response.json()
            audio_content = data.get("audioContent", "")
            return base64.b64decode(audio_content)

    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get Google Cloud TTS voices."""
        return [
            # US English Neural Voices
            {"id": "en-US-Neural2-A", "name": "US Neural Male A", "description": "Male, clear and professional", "language": "en-US", "gender": "male"},
            {"id": "en-US-Neural2-C", "name": "US Neural Female C", "description": "Female, warm and friendly", "language": "en-US", "gender": "female"},
            {"id": "en-US-Neural2-D", "name": "US Neural Male D", "description": "Male, authoritative", "language": "en-US", "gender": "male"},
            {"id": "en-US-Neural2-F", "name": "US Neural Female F", "description": "Female, energetic and engaging", "language": "en-US", "gender": "female"},
            {"id": "en-US-Neural2-G", "name": "US Neural Female G", "description": "Female, soft and gentle", "language": "en-US", "gender": "female"},
            {"id": "en-US-Neural2-H", "name": "US Neural Female H", "description": "Female, conversational", "language": "en-US", "gender": "female"},
            {"id": "en-US-Neural2-I", "name": "US Neural Male I", "description": "Male, deep and resonant", "language": "en-US", "gender": "male"},
            {"id": "en-US-Neural2-J", "name": "US Neural Male J", "description": "Male, casual and friendly", "language": "en-US", "gender": "male"},
            # UK English Neural Voices
            {"id": "en-GB-Neural2-A", "name": "UK Neural Female A", "description": "British female, elegant", "language": "en-GB", "gender": "female"},
            {"id": "en-GB-Neural2-B", "name": "UK Neural Male B", "description": "British male, sophisticated", "language": "en-GB", "gender": "male"},
            {"id": "en-GB-Neural2-C", "name": "UK Neural Female C", "description": "British female, professional", "language": "en-GB", "gender": "female"},
            {"id": "en-GB-Neural2-D", "name": "UK Neural Male D", "description": "British male, authoritative", "language": "en-GB", "gender": "male"},
            # Australian English Neural Voices
            {"id": "en-AU-Neural2-A", "name": "AU Neural Female A", "description": "Australian female, friendly", "language": "en-AU", "gender": "female"},
            {"id": "en-AU-Neural2-B", "name": "AU Neural Male B", "description": "Australian male, casual", "language": "en-AU", "gender": "male"},
            {"id": "en-AU-Neural2-C", "name": "AU Neural Female C", "description": "Australian female, warm", "language": "en-AU", "gender": "female"},
            {"id": "en-AU-Neural2-D", "name": "AU Neural Male D", "description": "Australian male, professional", "language": "en-AU", "gender": "male"},
        ]


class TTSProviderFactory:
    """Factory to get TTS providers (OpenAI and Google Cloud TTS)."""

    _providers = {
        "openai": OpenAITTSProvider,
        "google-cloud": GoogleCloudTTSProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> TTSProvider:
        """Get TTS provider instance by name."""
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown TTS provider: {provider_name}")
        return provider_class()

    @classmethod
    def get_available_providers(cls) -> List[Dict[str, any]]:
        """Get list of available providers with their configuration status."""
        print("\n" + "=" * 70)
        print("🔊 [TTSProviderFactory] Getting available providers...")
        print("=" * 70)

        logger.info("=" * 70)
        logger.info("[TTSProviderFactory] Getting available providers...")
        logger.info("=" * 70)

        providers = []
        for name, provider_class in cls._providers.items():
            print(f"\n🔍 [TTSProviderFactory] Checking provider: {name}")
            logger.info(f"[TTSProviderFactory] Checking provider: {name}")

            instance = provider_class()
            is_configured = instance.is_configured()

            provider_info = {
                "id": name,
                "name": name.replace("-", " ").title(),
                "configured": is_configured,
            }
            providers.append(provider_info)

            status_icon = "✅" if is_configured else "❌"
            print(f"{status_icon} [TTSProviderFactory] Provider '{name}': configured={is_configured}")
            logger.info(f"[TTSProviderFactory] Provider '{name}': {provider_info}")

        configured_count = sum(1 for p in providers if p['configured'])
        print(f"\n📊 [TTSProviderFactory] Summary:")
        print(f"   - Total providers: {len(providers)}")
        print(f"   - Configured: {configured_count}")
        print(f"   - Not configured: {len(providers) - configured_count}")
        print(f"   - Provider list: {providers}")
        print("=" * 70 + "\n")

        logger.info(f"[TTSProviderFactory] Total providers: {len(providers)}")
        logger.info(f"[TTSProviderFactory] Configured providers: {configured_count}")
        logger.info(f"[TTSProviderFactory] Final provider list: {providers}")
        logger.info("=" * 70)

        return providers

    @classmethod
    def get_default_provider(cls) -> Optional[TTSProvider]:
        """Get the first configured provider."""
        for provider_class in cls._providers.values():
            instance = provider_class()
            if instance.is_configured():
                return instance
        return None
