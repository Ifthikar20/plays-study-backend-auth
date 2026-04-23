"""
IDOR-safe permissions — every queryset is scoped to request.user.
This is the core security fix: no user can access another user's data.
"""
from rest_framework.permissions import BasePermission


class IsSessionOwner(BasePermission):
    """
    Ensures the requesting user owns the study session.
    Works on StudySession objects and on child objects (Topic, Question)
    by traversing relationships up to the session's user_id.
    """

    def has_object_permission(self, request, view, obj):
        # Direct session ownership
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id

        # Topic → session → user
        if hasattr(obj, 'study_session'):
            return obj.study_session.user_id == request.user.id

        # Question/Flashcard → topic → session → user
        if hasattr(obj, 'topic'):
            return obj.topic.study_session.user_id == request.user.id

        return False
