"""Study admin registration."""
from django.contrib import admin
from .models import StudySession, Topic, Question, Flashcard


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'progress', 'created_at')
    list_filter = ('status', 'file_type')
    search_fields = ('title', 'user__email')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'study_session', 'is_category', 'completed', 'order_index')
    list_filter = ('is_category', 'completed')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'topic', 'correct_answer')


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('front', 'topic', 'difficulty')
