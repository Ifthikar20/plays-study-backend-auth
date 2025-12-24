"""
Text-to-Speech API endpoints.
"""
import logging
import httpx
import re
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.services.tts_service import tts_service
from app.dependencies import get_current_user, get_db
from app.core.rate_limit import limiter
from slowapi import Limiter
from fastapi import Request
from app.config import settings
from app.models.topic import Topic

logger = logging.getLogger(__name__)

router = APIRouter()


class TTSRequest(BaseModel):
    """Request model for TTS generation."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to convert to speech")
    provider: str = Field(default="google-cloud", description="TTS provider (google-cloud)")
    voice: Optional[str] = Field(default=None, description="Voice ID to use")
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed")
    pitch: Optional[float] = Field(default=0.0, ge=-20.0, le=20.0, description="Voice pitch")
    model: Optional[str] = Field(default=None, description="Deprecated - not used")


class TTSProviderInfo(BaseModel):
    """TTS provider information."""
    id: str
    name: str
    configured: bool


class VoiceInfo(BaseModel):
    """Voice information."""
    id: str
    name: str
    description: str
    language: Optional[str] = None
    gender: Optional[str] = None


@router.post(
    "/tts/generate",
    response_class=Response,
    summary="Generate speech from text",
    description="Convert text to speech using AI voices. Returns MP3 audio data.",
)
@limiter.limit("30/minute")  # Rate limit: 30 requests per minute per user
async def generate_speech(
    request: Request,
    tts_request: TTSRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate speech from text using Google Cloud Text-to-Speech.

    - **text**: Text to convert (max 5000 characters)
    - **provider**: TTS provider (google-cloud)
    - **voice**: Voice ID (e.g., en-US-Neural2-F)
    - **speed**: Speaking speed (0.25 to 4.0)
    - **pitch**: Voice pitch (-20 to 20)

    Returns MP3 audio data that can be played in a browser.
    """
    try:
        logger.info("=" * 60)
        logger.info("[API /tts/generate] TTS generation requested")
        logger.info(f"[API /tts/generate] User: {current_user.email}")
        logger.info(f"[API /tts/generate] Provider: {tts_request.provider}")
        logger.info(f"[API /tts/generate] Voice: {tts_request.voice}")
        logger.info(f"[API /tts/generate] Text length: {len(tts_request.text)} chars")

        # Prepare parameters for Google Cloud TTS
        kwargs = {
            "speed": tts_request.speed,
            "pitch": tts_request.pitch,
            "volume_gain_db": 0.0,
        }

        # Generate speech
        logger.info(f"[API /tts/generate] Calling tts_service.generate_speech()...")
        audio_data = await tts_service.generate_speech(
            text=tts_request.text,
            provider_name=tts_request.provider,
            voice=tts_request.voice,
            **kwargs
        )

        logger.info(f"[API /tts/generate] ✅ Successfully generated {len(audio_data)} bytes of audio")
        logger.info("=" * 60)

        # Return audio as MP3
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                "Content-Disposition": "inline; filename=speech.mp3",
            }
        )

    except ValueError as e:
        logger.error(f"[API /tts/generate] ❌ ValueError: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[API /tts/generate] ❌ Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {str(e)}"
        )


@router.get(
    "/tts/providers",
    response_model=List[TTSProviderInfo],
    summary="Get available TTS providers",
    description="List all TTS providers and their configuration status",
)
async def get_providers(
    current_user: dict = Depends(get_current_user),
):
    """
    Get list of available TTS providers.

    Returns information about each provider including whether it's configured.
    """
    try:
        print("\n" + "=" * 70)
        print("🔊 [API /tts/providers] Endpoint called")
        print(f"👤 User: {current_user.email}")
        print("=" * 70)

        logger.info("=" * 70)
        logger.info("[API /tts/providers] Endpoint called")
        logger.info(f"[API /tts/providers] User: {current_user.email}")

        providers = tts_service.get_available_providers()

        print(f"\n📋 [API /tts/providers] Returning {len(providers)} providers:")
        for provider in providers:
            status_icon = "✅" if provider['configured'] else "❌"
            print(f"  {status_icon} {provider['id']}: configured={provider['configured']}")
        print("=" * 70 + "\n")

        logger.info(f"[API /tts/providers] Returning {len(providers)} providers:")
        for provider in providers:
            logger.info(f"  - {provider['id']}: configured={provider['configured']}")
        logger.info("=" * 70)

        return providers
    except Exception as e:
        logger.error(f"[API /tts/providers] Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get providers: {str(e)}"
        )


@router.get(
    "/tts/voices",
    response_model=Dict[str, List[VoiceInfo]],
    summary="Get available voices",
    description="Get all available voices grouped by provider",
)
async def get_voices(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all available voices grouped by provider.

    Returns a dictionary with provider names as keys and lists of voices as values.
    Only includes voices from configured providers.
    """
    try:
        voices = tts_service.get_all_voices()
        return voices
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voices: {str(e)}"
        )


@router.get(
    "/tts/voices/{provider}",
    response_model=List[VoiceInfo],
    summary="Get voices for a specific provider",
    description="Get available voices for a specific TTS provider",
)
async def get_provider_voices(
    provider: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get available voices for a specific provider.

    - **provider**: Provider name (openai or google-cloud)
    """
    try:
        voices = tts_service.get_provider_voices(provider)
        return voices
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voices: {str(e)}"
        )


class MentorContentRequest(BaseModel):
    """Request model for mentor content generation."""
    topic_id: Optional[int] = Field(None, description="Topic ID to save narrative to")
    topic_title: str = Field(..., description="Title of the topic")
    topic_description: Optional[str] = Field(None, description="Description of the topic")
    questions: List[Dict] = Field(..., description="List of questions with options and correct answers")


class MentorContentResponse(BaseModel):
    """Response model for mentor content."""
    narrative: str = Field(..., description="Formatted narrative for the mentor")
    estimated_duration_seconds: int = Field(..., description="Estimated speech duration")
    mermaid_code: Optional[str] = Field(default=None, description="Mermaid diagram code for visual representation")
    key_terms: Optional[List[str]] = Field(default=None, description="List of important key terms")


@router.post(
    "/tts/generate-mentor-content",
    response_model=MentorContentResponse,
    summary="Generate AI mentor content",
    description="Use DeepSeek AI to generate comprehensive, structured mentor content with examples",
)
@limiter.limit("10/minute")
async def generate_mentor_content(
    request: Request,
    content_request: MentorContentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate comprehensive mentor content using DeepSeek AI.

    Creates extensive, teacher-style explanations with:
    - Real-world examples
    - Bullet points
    - Why it matters sections
    - Multiple perspectives
    - Formatted for text-to-speech
    """
    try:
        logger.info(f"[Mentor Content] Request for topic: {content_request.topic_title}")

        # Check if narrative already exists for this topic (decrypt if needed)
        if content_request.topic_id:
            logger.info(f"[Mentor Content] Checking database for topic_id={content_request.topic_id}")
            topic = db.query(Topic).filter(Topic.id == content_request.topic_id).first()
            if topic:
                # Use decryption getter to retrieve narrative
                cached_narrative = topic.get_mentor_narrative()
                if cached_narrative:
                    logger.info(f"[Mentor Content] ✅ CACHE HIT - Returning cached (decrypted) narrative for topic {content_request.topic_id}")
                    word_count = len(cached_narrative.split())
                    estimated_seconds = int((word_count / 150) * 60)
                    return MentorContentResponse(
                        narrative=cached_narrative,
                        estimated_duration_seconds=estimated_seconds
                    )
                else:
                    logger.info(f"[Mentor Content] ⚠️ Topic exists but no cached narrative - will generate new")
            else:
                logger.info(f"[Mentor Content] ⚠️ Topic ID {content_request.topic_id} not found in database - will generate new")

        logger.info(f"[Mentor Content] Generating new content for: {content_request.topic_title}")

        # Build the prompt for DeepSeek
        prompt = f"""You are a friendly AI tutor explaining concepts clearly and naturally.

Topic: {content_request.topic_title}
Description: {content_request.topic_description or 'No description provided'}

Create a natural, conversational lesson that covers the following concepts:
"""

        # Add each question/concept
        for idx, q in enumerate(content_request.questions, 1):
            question = q.get('question', '')
            correct_answer = q.get('options', [''])[q.get('correctAnswer', 0)]
            explanation = q.get('explanation', '')

            prompt += f"\n{idx}. {question}\n"
            if correct_answer:
                prompt += f"   Answer: {correct_answer}\n"
            if explanation:
                prompt += f"   Context: {explanation}\n"

        prompt += """

Guidelines:
- Start with a brief, friendly introduction (1-2 sentences)
- For each concept, explain it clearly with 1-2 relevant examples
- Use simple, conversational language as if talking to a student
- Break complex ideas into digestible pieces
- End each concept with a brief "why it matters" note
- Keep it focused and avoid excessive repetition
- Use minimal formatting - occasional bullet points are fine, but don't overuse emojis
- Aim for clarity and engagement over rigid structure

IMPORTANT: Mark key terms and important vocabulary words that students should remember.
Wrap them like this: **TERM:photosynthesis** or **TERM:French Revolution**
These will be highlighted for students. Mark 5-10 important terms throughout your explanation.

IMPORTANT: After your explanation, create a Mermaid diagram to visualize the key concepts.
Add this section at the very end:

---MERMAID---
[Your Mermaid.js diagram code here]
---END_MERMAID---

Mermaid diagram guidelines:
- Use flowcharts (graph TD/LR), mindmaps, or sequence diagrams as appropriate
- Keep it simple and focused on the main concept
- Use clear, short labels
- Examples:
  * Flowchart: graph LR; A[Start] --> B[Process] --> C[End]
  * Mind map: mindmap
  root((Topic))
    Concept1
    Concept2
  * Sequence: sequenceDiagram; A->>B: Message

Write this as you would naturally explain it to a student, not following a strict template.
"""

        # Call DeepSeek AI (with extended timeout for comprehensive content generation)
        logger.info("[Mentor Content] Calling DeepSeek AI...")
        async with httpx.AsyncClient(timeout=180.0) as client:  # 3 minutes for long lessons
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a friendly, knowledgeable tutor who explains concepts clearly and naturally. You use simple language, relevant examples, and focus on helping students truly understand the material rather than memorizing facts."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                }
            )

        if response.status_code != 200:
            logger.error(f"[Mentor Content] DeepSeek API error: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate content from AI"
            )

        result = response.json()
        full_content = result['choices'][0]['message']['content']

        # Extract Mermaid diagram code if present
        # Handle both "---END_MERMAID---" and "---END MERMAID---" variations
        mermaid_code = None
        narrative = full_content

        # Use regex to handle various end marker formats
        mermaid_pattern = r'---MERMAID---(.*?)---END[_\s]?MERMAID---'
        mermaid_match = re.search(mermaid_pattern, full_content, re.DOTALL | re.IGNORECASE)

        if mermaid_match:
            # Extract the Mermaid code
            mermaid_code = mermaid_match.group(1).strip()
            # Remove the entire Mermaid section from the narrative
            narrative = re.sub(mermaid_pattern, '', full_content, flags=re.DOTALL | re.IGNORECASE).strip()
            logger.info(f"[Mentor Content] 📊 Extracted Mermaid diagram ({len(mermaid_code)} chars)")
        else:
            logger.info(f"[Mentor Content] ℹ️ No Mermaid diagram found in content")

        # Extract key terms from narrative
        # Pattern: **TERM:word** or **TERM:multiple words**
        key_terms = []
        term_pattern = r'\*\*TERM:(.*?)\*\*'
        matches = re.findall(term_pattern, narrative)
        if matches:
            key_terms = list(set(matches))  # Remove duplicates
            logger.info(f"[Mentor Content] 🔑 Extracted {len(key_terms)} key terms")

        # Estimate duration (average speaking rate: ~150 words per minute)
        # Count words excluding the TERM markers
        clean_text = re.sub(term_pattern, r'\1', narrative)
        word_count = len(clean_text.split())
        estimated_seconds = int((word_count / 150) * 60)

        logger.info(f"[Mentor Content] ✅ Generated {word_count} words (~{estimated_seconds}s)")

        # Save narrative to topic if topic_id provided (with encryption)
        if content_request.topic_id:
            topic = db.query(Topic).filter(Topic.id == content_request.topic_id).first()
            if topic:
                # Use encrypted setter (encrypts data at rest)
                topic.set_mentor_narrative(narrative)
                db.commit()
                logger.info(f"[Mentor Content] 💾 Saved encrypted narrative to topic {content_request.topic_id}")

        return MentorContentResponse(
            narrative=narrative,
            estimated_duration_seconds=estimated_seconds,
            mermaid_code=mermaid_code,
            key_terms=key_terms if key_terms else None
        )

    except httpx.TimeoutException:
        logger.error("[Mentor Content] DeepSeek API timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI content generation timed out"
        )
    except Exception as e:
        logger.error(f"[Mentor Content] Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate mentor content: {str(e)}"
        )
