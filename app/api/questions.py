"""
Question generation API endpoint using DeepSeek.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List
from openai import OpenAI
from app.config import settings
from app.dependencies import get_current_active_user
from app.models.user import User
from app.core.rate_limit import limiter

router = APIRouter()


class QuestionGenerationRequest(BaseModel):
    """Request schema for generating questions."""
    topic: str = Field(..., min_length=1, max_length=500, description="The topic to generate questions about")
    num_questions: int = Field(default=5, ge=1, le=20, description="Number of questions to generate")
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$", description="Difficulty level")


class Question(BaseModel):
    """Schema for a single generated question."""
    id: str
    question: str
    options: List[str]
    correctAnswer: int
    explanation: str


class QuestionGenerationResponse(BaseModel):
    """Response schema for generated questions."""
    topic: str
    questions: List[Question]


@router.post("/generate-questions", response_model=QuestionGenerationResponse)
@limiter.limit("10/minute")
async def generate_questions(
    request: Request,
    data: QuestionGenerationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate quiz questions using DeepSeek.

    Args:
        request: FastAPI request object (required for rate limiting)
        data: Question generation parameters
        current_user: The authenticated user

    Returns:
        Generated questions with options and explanations

    Rate Limits:
        - 10 requests per minute per user
    """
    try:
        # Initialize DeepSeek client (OpenAI-compatible)
        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )

        # Create prompt for DeepSeek
        prompt = f"""Generate {data.num_questions} multiple-choice questions about the topic: "{data.topic}".

Difficulty level: {data.difficulty}

Requirements:
1. Each question should have exactly 4 options (A, B, C, D)
2. Include the correct answer index (0-3)
3. Provide a brief explanation for each answer
4. Questions should be educational and accurate
5. Format the response as a valid JSON array

Return the questions in this EXACT JSON format:
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correctAnswer": 0,
      "explanation": "Explanation of why this answer is correct"
    }}
  ]
}}

Generate {data.num_questions} questions now."""

        # Call DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=4096,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract the response
        response_text = response.choices[0].message.content

        # Parse the JSON response
        import json

        # Try to extract JSON from the response
        try:
            # Find JSON object in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            parsed_data = json.loads(json_str)

            # Extract questions
            questions_data = parsed_data.get("questions", [])

            # Format questions with IDs
            formatted_questions = []
            for idx, q in enumerate(questions_data):
                formatted_questions.append(Question(
                    id=f"{data.topic.lower().replace(' ', '_')}_{idx + 1}",
                    question=q["question"],
                    options=q["options"],
                    correctAnswer=q["correctAnswer"],
                    explanation=q["explanation"]
                ))

            return QuestionGenerationResponse(
                topic=data.topic,
                questions=formatted_questions
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response: {str(e)}"
            )

    except Exception as api_error:
        if "openai" in str(type(api_error).__module__):
            raise HTTPException(
                status_code=500,
                detail=f"DeepSeek API error: {str(api_error)}"
            )
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions: {str(e)}"
        )
