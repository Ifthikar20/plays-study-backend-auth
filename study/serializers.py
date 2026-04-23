"""Serializers for the study app."""
from rest_framework import serializers
from .models import StudySession, Topic, Question, Flashcard


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    correctAnswer = serializers.IntegerField(source='correct_answer')
    sourceText = serializers.CharField(source='source_text', allow_null=True, required=False)
    sourcePage = serializers.IntegerField(source='source_page', allow_null=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'question', 'options', 'correctAnswer', 'explanation', 'sourceText', 'sourcePage']

    def get_id(self, obj):
        return f'q-{obj.id}'


class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = ['id', 'front', 'back', 'hint']


class TopicSerializer(serializers.ModelSerializer):
    """Nested topic with questions and subtopics."""
    id = serializers.SerializerMethodField()
    db_id = serializers.IntegerField(source='pk', read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    flashcards = FlashcardSerializer(many=True, read_only=True)
    subtopics = serializers.SerializerMethodField()
    isCategory = serializers.BooleanField(source='is_category')
    parentTopicId = serializers.SerializerMethodField()
    currentQuestionIndex = serializers.IntegerField(source='current_question_index')
    workflowStage = serializers.CharField(source='workflow_stage', required=False)

    class Meta:
        model = Topic
        fields = [
            'id', 'db_id', 'title', 'description', 'questions', 'flashcards',
            'completed', 'score', 'currentQuestionIndex', 'isCategory',
            'parentTopicId', 'subtopics', 'workflowStage',
        ]

    def get_id(self, obj):
        if obj.is_category:
            return f'category-{obj.order_index + 1}'
        return f'subtopic-{obj.order_index + 1}'

    def get_parentTopicId(self, obj):
        if obj.parent_topic:
            return f'category-{obj.parent_topic.order_index + 1}'
        return None

    def get_subtopics(self, obj):
        if obj.is_category:
            children = obj.subtopics.all().order_by('order_index')
            return TopicSerializer(children, many=True).data
        return []


class StudySessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for session lists."""
    createdAt = serializers.SerializerMethodField()
    fileType = serializers.CharField(source='file_type', allow_null=True)
    hasFullStudy = serializers.BooleanField(source='has_full_study')
    hasSpeedRun = serializers.BooleanField(source='has_speed_run')
    topicsCount = serializers.IntegerField(source='topics_count')

    class Meta:
        model = StudySession
        fields = [
            'id', 'title', 'topic', 'progress', 'topicsCount',
            'hasFullStudy', 'hasSpeedRun', 'fileType', 'status', 'createdAt',
        ]

    def get_createdAt(self, obj):
        if obj.created_at:
            return int(obj.created_at.timestamp() * 1000)
        return None


class StudySessionDetailSerializer(serializers.ModelSerializer):
    """Full session with topics, questions, and file content."""
    extractedTopics = serializers.SerializerMethodField()
    studyContent = serializers.CharField(source='study_content', allow_null=True)
    fileContent = serializers.CharField(source='file_content', allow_null=True)
    fileType = serializers.CharField(source='file_type', allow_null=True)
    pdfContent = serializers.CharField(source='pdf_content', allow_null=True)
    hasFullStudy = serializers.BooleanField(source='has_full_study')
    hasSpeedRun = serializers.BooleanField(source='has_speed_run')
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = StudySession
        fields = [
            'id', 'title', 'studyContent', 'fileContent', 'fileType', 'pdfContent',
            'extractedTopics', 'progress', 'hasFullStudy', 'hasSpeedRun', 'createdAt',
        ]

    def get_createdAt(self, obj):
        if obj.created_at:
            return int(obj.created_at.timestamp() * 1000)
        return None

    def get_extractedTopics(self, obj):
        # Only top-level categories (no parent)
        root_topics = obj.topics.filter(parent_topic__isnull=True).order_by('order_index')
        return TopicSerializer(root_topics, many=True).data
