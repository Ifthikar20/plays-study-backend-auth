"""
Study views — IDOR-safe API endpoints.
Every queryset is filtered by request.user to prevent unauthorized access.
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import StudySession, Topic, Question, Flashcard
from .serializers import StudySessionListSerializer, StudySessionDetailSerializer
from .permissions import IsSessionOwner

logger = logging.getLogger(__name__)


# ─── App Data (Dashboard) ────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def app_data(request):
    """
    GET /api/app-data
    Consolidated dashboard data — sessions, stats, user info.
    IDOR-safe: only returns current user's sessions.
    """
    user = request.user
    sessions = StudySession.objects.filter(user=user).order_by('-created_at')

    total_sessions = sessions.count()
    completed_sessions = sessions.filter(is_completed=True).count()
    total_xp = user.xp

    return Response({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'xp': user.xp,
            'level': user.level,
        },
        'stats': {
            'totalSessions': total_sessions,
            'completedSessions': completed_sessions,
            'totalXP': total_xp,
            'level': user.level,
        },
        'studySessions': StudySessionListSerializer(sessions, many=True).data,
    })


# ─── Study Sessions CRUD ─────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_list(request):
    """
    GET /api/study-sessions/
    List all sessions for the current user.
    """
    sessions = StudySession.objects.filter(user=request.user)
    return Response(StudySessionListSerializer(sessions, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_detail(request, session_id):
    """
    GET /api/study-sessions/<uuid>/
    Get full session detail with topics and questions.
    IDOR-safe: filters by user.
    """
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    return Response(StudySessionDetailSerializer(session).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def session_delete(request, session_id):
    """
    DELETE /api/study-sessions/<uuid>/
    Delete a session. IDOR-safe: verifies ownership.
    """
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    session.delete()
    return Response({'detail': 'Session deleted'}, status=status.HTTP_200_OK)


# ─── Content Analysis ────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_content(request):
    """
    POST /api/study-sessions/analyze-content
    Analyze uploaded content and return recommendations.
    """
    from study.services.ai_service import extract_text, analyze_complexity

    content = request.data.get('content', '')
    if not content or len(content.strip()) < 50:
        return Response(
            {'detail': 'Content too short. Provide at least 50 characters.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        extracted = extract_text(content)
        analysis = analyze_complexity(extracted)

        return Response({
            'word_count': analysis['word_count'],
            'estimated_reading_time': analysis['estimated_reading_time'],
            'recommended_topics': analysis['recommended_topics'],
            'recommended_questions': analysis['recommended_questions'],
            'complexity_score': analysis['complexity_score'],
            'content_summary': extracted[:200] + ('...' if len(extracted) > 200 else ''),
        })
    except Exception as e:
        logger.error(f'Content analysis failed: {e}')
        return Response(
            {'detail': f'Failed to analyze content: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─── AI Session Creation ─────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_with_ai(request):
    """
    POST /api/study-sessions/create-with-ai
    Create a study session with AI-generated topics and questions.
    IDOR-safe: session is always created under request.user.
    """
    from study.services.ai_service import (
        detect_file_type,
        analyze_complexity,
        generate_topics_and_questions,
        ensure_flashcards_on_subtopic,
        _sentences,
    )

    title = request.data.get('title', '')
    content = request.data.get('content', '')
    num_topics = request.data.get('num_topics', 4)
    questions_per_topic = request.data.get('questions_per_topic', 15)

    if not title or not content:
        return Response(
            {'detail': 'Title and content are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        extracted_text, file_type, file_content = detect_file_type(content)

        if not extracted_text or len(extracted_text.strip()) < 50:
            return Response(
                {'detail': 'Content too short or empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        analysis = analyze_complexity(extracted_text)

        # Generate topics, questions, and flashcards using AI (or the deterministic fallback).
        topics_data = generate_topics_and_questions(
            extracted_text, num_topics, questions_per_topic
        )

        source_sentences = _sentences(extracted_text)
        flashcards_created = 0
        questions_created = 0

        with transaction.atomic():
            # Create the study session.
            session = StudySession.objects.create(
                user=request.user,
                title=title,
                topic=title,
                study_content=extracted_text,
                file_content=file_content,
                file_type=file_type,
                topics_count=min(num_topics, analysis['recommended_topics']),
                has_full_study=True,
                has_speed_run=True,
                status='in_progress',
            )

            # Save topics, subtopics, questions, and flashcards.
            for idx, t_data in enumerate(topics_data):
                category = Topic.objects.create(
                    study_session=session,
                    title=t_data['title'],
                    description=t_data.get('description', ''),
                    order_index=idx,
                    is_category=True,
                )

                for sub_idx, sub_data in enumerate(t_data.get('subtopics', [])):
                    subtopic = Topic.objects.create(
                        study_session=session,
                        parent_topic=category,
                        title=sub_data['title'],
                        description=sub_data.get('description', ''),
                        order_index=sub_idx,
                        is_category=False,
                        workflow_stage='quiz_available' if idx == 0 and sub_idx == 0 else 'locked',
                    )

                    for q_idx, q_data in enumerate(sub_data.get('questions', [])):
                        Question.objects.create(
                            topic=subtopic,
                            question=q_data['question'],
                            options=q_data.get('options', []),
                            correct_answer=q_data.get('correct_answer', 0),
                            explanation=q_data.get('explanation', ''),
                            source_text=q_data.get('source_text'),
                            source_page=q_data.get('source_page'),
                            order_index=q_idx,
                        )
                        questions_created += 1

                    # Flashcards — fall back to deriving from questions if the AI didn't return any.
                    flashcards = ensure_flashcards_on_subtopic(sub_data, source_sentences)
                    for fc_idx, fc in enumerate(flashcards):
                        front = (fc.get('front') or '').strip()
                        back = (fc.get('back') or '').strip()
                        if not front or not back:
                            continue
                        Flashcard.objects.create(
                            topic=subtopic,
                            front=front,
                            back=back,
                            hint=(fc.get('hint') or None),
                            order_index=fc_idx,
                        )
                        flashcards_created += 1

        session.refresh_from_db()
        logger.info(
            'Session %s created for %s — %d questions, %d flashcards',
            session.id, request.user.email, questions_created, flashcards_created,
        )

        return Response({
            'id': str(session.id),
            'title': session.title,
            'studyContent': session.study_content,
            'fileContent': session.file_content,
            'fileType': session.file_type,
            'pdfContent': session.pdf_content,
            'extractedTopics': StudySessionDetailSerializer(session).data.get('extractedTopics', []),
            'progress': 0,
            'topics': session.topics_count,
            'hasFullStudy': True,
            'hasSpeedRun': True,
            'createdAt': int(session.created_at.timestamp() * 1000),
            'progressiveLoad': False,
            'questionsRemaining': 0,
            'redirectUrl': f'/study/full/{session.id}',
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f'AI session creation failed: {e}', exc_info=True)
        return Response(
            {'detail': f'Failed to create study session: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─── Progress Updates ────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_progress(request, session_id):
    """
    POST /api/study-sessions/<uuid>/progress
    Update topic progress. IDOR-safe.
    """
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    updates = request.data.get('updates', [])

    for update in updates:
        topic_db_id = update.get('topicDbId')
        if not topic_db_id:
            continue
        try:
            topic = Topic.objects.get(id=topic_db_id, study_session=session)
            if 'completed' in update:
                topic.completed = update['completed']
            if 'score' in update:
                topic.score = update['score']
            if 'currentQuestionIndex' in update:
                topic.current_question_index = update['currentQuestionIndex']
            topic.save()
        except Topic.DoesNotExist:
            continue

    # Recalculate session progress
    total = session.topics.filter(is_category=False).count()
    done = session.topics.filter(is_category=False, completed=True).count()
    session.progress = int((done / max(total, 1)) * 100)
    session.save()

    return Response({'progress': session.progress})
