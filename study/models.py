"""Study models — StudySession, Topic, Question, Flashcard."""
import uuid
from django.conf import settings
from django.db import models


class StudySession(models.Model):
    """Study session with file content, topics, and progress tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_sessions')
    title = models.CharField(max_length=255)
    topic = models.CharField(max_length=255)
    study_content = models.TextField(blank=True, null=True)
    file_content = models.TextField(blank=True, null=True)
    file_type = models.CharField(max_length=10, blank=True, null=True)
    pdf_content = models.TextField(blank=True, null=True)
    duration = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)
    topics_count = models.IntegerField(default=0)
    xp_earned = models.IntegerField(default=0)
    accuracy = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, default='in_progress')
    is_completed = models.BooleanField(default=False)
    has_full_study = models.BooleanField(default=False)
    has_speed_run = models.BooleanField(default=False)
    has_quiz = models.BooleanField(default=False)
    folder = models.ForeignKey('folders.Folder', on_delete=models.SET_NULL, null=True, blank=True, related_name='study_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'study_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.user.email})'


class Topic(models.Model):
    """Hierarchical topic within a study session."""
    study_session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name='topics')
    parent_topic = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtopics')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    order_index = models.IntegerField(default=0)
    page_number = models.IntegerField(blank=True, null=True)
    is_category = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    score = models.IntegerField(blank=True, null=True)
    current_question_index = models.IntegerField(default=0)
    mentor_narrative = models.TextField(blank=True, null=True)
    workflow_stage = models.CharField(max_length=30, default='locked')
    position_x = models.FloatField(blank=True, null=True)
    position_y = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'topics'
        ordering = ['order_index']

    def __str__(self):
        return self.title


class Question(models.Model):
    """Quiz question belonging to a topic."""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    options = models.JSONField(default=list)
    correct_answer = models.IntegerField()
    explanation = models.TextField(blank=True, default='')
    source_text = models.TextField(blank=True, null=True)
    source_page = models.IntegerField(blank=True, null=True)
    order_index = models.IntegerField(default=0)

    class Meta:
        db_table = 'questions'
        ordering = ['order_index']

    def __str__(self):
        return self.question[:80]


class Flashcard(models.Model):
    """Flashcard for memory review."""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='flashcards')
    front = models.TextField()
    back = models.TextField()
    hint = models.TextField(blank=True, null=True)
    order_index = models.IntegerField(default=0)
    difficulty = models.CharField(max_length=20, default='medium')
    times_reviewed = models.IntegerField(default=0)
    last_reviewed = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'flashcards'
        ordering = ['order_index']

    def __str__(self):
        return self.front[:80]
