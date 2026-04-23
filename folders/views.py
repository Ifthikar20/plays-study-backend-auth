"""Folder API — IDOR-safe CRUD."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Folder

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def folder_list_create(request):
    """
    GET  /api/folders/ — list user's folders
    POST /api/folders/ — create a new folder
    """
    if request.method == 'GET':
        folders = Folder.objects.filter(user=request.user, is_archived=False)
        data = [{
            'id': f.id,
            'name': f.name,
            'color': f.color,
            'icon': f.icon,
            'sessionCount': f.study_sessions.count(),
            'createdAt': int(f.created_at.timestamp() * 1000),
        } for f in folders]
        return Response(data)

    # POST
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'detail': 'Folder name is required'}, status=status.HTTP_400_BAD_REQUEST)

    folder = Folder.objects.create(
        user=request.user,
        name=name,
        color=request.data.get('color', '#3B82F6'),
        icon=request.data.get('icon', '📁'),
    )
    return Response({
        'id': folder.id,
        'name': folder.name,
        'color': folder.color,
        'icon': folder.icon,
        'sessionCount': 0,
        'createdAt': int(folder.created_at.timestamp() * 1000),
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def folder_detail(request, folder_id):
    """
    PUT    /api/folders/<id>/ — update folder
    DELETE /api/folders/<id>/ — delete folder (IDOR-safe)
    """
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)

    if request.method == 'DELETE':
        folder.delete()
        return Response({'detail': 'Folder deleted'})

    # PUT
    if 'name' in request.data:
        folder.name = request.data['name']
    if 'color' in request.data:
        folder.color = request.data['color']
    if 'icon' in request.data:
        folder.icon = request.data['icon']
    folder.save()

    return Response({
        'id': folder.id,
        'name': folder.name,
        'color': folder.color,
        'icon': folder.icon,
    })
