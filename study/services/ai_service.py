"""
AI service — content extraction, analysis, and topic/question generation.
Ported from FastAPI study_sessions.py to a clean Django service.
"""
import io
import json
import logging
import base64
from django.conf import settings

logger = logging.getLogger(__name__)


# ─── Text Extraction ──────────────────────────────────────

def extract_text(content: str) -> str:
    """Extract readable text from content (plain text, base64 PDF/DOCX/PPTX)."""
    _, _, text = detect_file_type(content)
    return text


def detect_file_type(content: str) -> tuple:
    """
    Detect file type and extract text.
    Returns: (extracted_text, file_type, original_content)
    """
    content_bytes = None
    file_type = 'txt'

    try:
        decoded = base64.b64decode(content, validate=False)
        if decoded.startswith(b'PK\x03\x04') or decoded.startswith(b'%PDF'):
            content_bytes = decoded
    except Exception:
        pass

    if content_bytes:
        if content_bytes.startswith(b'PK\x03\x04'):
            # Try PowerPoint
            try:
                from pptx import Presentation
                prs = Presentation(io.BytesIO(content_bytes))
                parts = []
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, 'text') and shape.text.strip():
                            parts.append(shape.text)
                text = '\n'.join(parts)
                if text.strip():
                    return (text, 'pptx', content)
            except Exception:
                pass

            # Try Word
            try:
                from docx import Document
                doc = Document(io.BytesIO(content_bytes))
                text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
                if text.strip():
                    return (text, 'docx', content)
            except Exception:
                pass

        elif content_bytes.startswith(b'%PDF'):
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(io.BytesIO(content_bytes))
                text = '\n'.join(page.extract_text() for page in reader.pages)
                if text.strip():
                    return (text, 'pdf', content)
            except Exception:
                pass

    cleaned = content.replace('\ufffd', '').strip()
    return (cleaned if len(cleaned) > 10 else content, 'txt', content)


# ─── Complexity Analysis ──────────────────────────────────

def analyze_complexity(text: str) -> dict:
    """Analyze content complexity and recommend topic/question counts."""
    words = text.split()
    word_count = len(words)
    unique_words = len(set(w.lower() for w in words if w.isalnum()))
    unique_ratio = unique_words / max(word_count, 1)
    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
    sentences = len([c for c in text if c in '.!?'])
    avg_sent_len = word_count / max(sentences, 1)

    complexity = min(1.0, unique_ratio * 0.4 + min(avg_word_len / 8, 1.0) * 0.3 + min(avg_sent_len / 25, 1.0) * 0.3)

    if word_count < 500:
        topics = 2
    elif word_count < 2000:
        topics = 4
    elif word_count < 5000:
        topics = 8
    else:
        topics = min(20, word_count // 500)

    questions = max(10, min(30, int(15 * (0.9 + complexity * 0.6))))

    return {
        'word_count': word_count,
        'estimated_reading_time': max(1, round(word_count / 225)),
        'recommended_topics': topics,
        'recommended_questions': questions,
        'complexity_score': round(complexity, 2),
    }


# ─── AI Topic/Question Generation ─────────────────────────

def generate_topics_and_questions(text: str, num_topics: int, questions_per_topic: int) -> list:
    """
    Use Anthropic/OpenAI to generate topics and questions from study content.
    Returns list of topic dicts with subtopics and questions.
    """
    # Try Anthropic first, then OpenAI
    if settings.ANTHROPIC_API_KEY:
        return _generate_with_anthropic(text, num_topics, questions_per_topic)
    elif settings.OPENAI_API_KEY:
        return _generate_with_openai(text, num_topics, questions_per_topic)
    else:
        logger.warning('No AI API key configured — generating placeholder topics')
        return _generate_placeholder(text, num_topics, questions_per_topic)


def _generate_with_anthropic(text: str, num_topics: int, qpt: int) -> list:
    """Generate using Claude."""
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = _build_prompt(text, num_topics, qpt)

    response = client.messages.create(
        model='claude-3-5-haiku-latest',
        max_tokens=8000,
        messages=[{'role': 'user', 'content': prompt}],
    )

    return _parse_ai_response(response.content[0].text)


def _generate_with_openai(text: str, num_topics: int, qpt: int) -> list:
    """Generate using OpenAI."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = _build_prompt(text, num_topics, qpt)

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=8000,
    )

    return _parse_ai_response(response.choices[0].message.content)


def _build_prompt(text: str, num_topics: int, qpt: int) -> str:
    """Build the AI prompt for topic/question generation."""
    # Truncate text if too long
    max_chars = 60000
    if len(text) > max_chars:
        text = text[:max_chars] + '\n\n[Content truncated for processing]'

    return f"""Analyze the following study material and create a structured learning plan.

Create {num_topics} main topic categories, each with 2-3 subtopics.
For each subtopic, generate {qpt} multiple-choice questions.

Return ONLY valid JSON in this exact format:
[
  {{
    "title": "Category Title",
    "description": "Brief description",
    "subtopics": [
      {{
        "title": "Subtopic Title",
        "description": "Brief description",
        "questions": [
          {{
            "question": "Question text?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0,
            "explanation": "Why A is correct"
          }}
        ]
      }}
    ]
  }}
]

STUDY MATERIAL:
{text}"""


def _parse_ai_response(text: str) -> list:
    """Parse the AI response JSON."""
    # Find JSON in the response
    start = text.find('[')
    end = text.rfind(']') + 1
    if start == -1 or end == 0:
        logger.error('No JSON array found in AI response')
        return []

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse AI JSON: {e}')
        return []


def _generate_placeholder(text: str, num_topics: int, qpt: int) -> list:
    """Generate simple placeholder topics when no AI key is available."""
    words = text.split()
    chunk_size = max(1, len(words) // max(num_topics, 1))
    topics = []

    for i in range(min(num_topics, 3)):
        chunk = ' '.join(words[i * chunk_size:(i + 1) * chunk_size])
        first_sentence = chunk.split('.')[0][:100] if chunk else f'Topic {i + 1}'

        questions = []
        for q in range(min(qpt, 5)):
            questions.append({
                'question': f'Sample question {q + 1} about {first_sentence[:50]}?',
                'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                'correct_answer': 0,
                'explanation': 'This is a placeholder question. Configure ANTHROPIC_API_KEY or OPENAI_API_KEY for real AI generation.',
            })

        topics.append({
            'title': f'Section {i + 1}: {first_sentence[:60]}',
            'description': first_sentence,
            'subtopics': [{
                'title': first_sentence[:80],
                'description': first_sentence,
                'questions': questions,
            }],
        })

    return topics
