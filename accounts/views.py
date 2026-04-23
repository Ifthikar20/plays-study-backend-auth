"""Auth views — register, login, refresh, logout, profile."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model, authenticate
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthRateThrottle(AnonRateThrottle):
    rate = '10/minute'


def _token_response(user):
    """Generate an access+refresh token pair with extra claims."""
    refresh = RefreshToken.for_user(user)
    refresh['email'] = user.email
    refresh['sub'] = str(user.id)
    access = refresh.access_token
    access['email'] = user.email
    access['sub'] = str(user.id)

    return {
        'access_token': str(access),
        'refresh_token': str(refresh),
        'token_type': 'bearer',
        'expires_in': int(access.lifetime.total_seconds()),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def register(request):
    """POST /api/auth/register — create account, return token pair."""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        first_error = next(iter(serializer.errors.values()))[0]
        return Response({'detail': str(first_error)}, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    logger.info('New user registered: %s', user.email)
    return Response(_token_response(user), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def login(request):
    """POST /api/auth/login — authenticate, return token pair."""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'detail': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].lower()
    password = serializer.validated_data['password']

    user = authenticate(request, username=email, password=password)
    if user is None:
        logger.warning('Login failed for: %s', email)
        return Response({'detail': 'Incorrect email or password'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        return Response({'detail': 'Account is inactive'}, status=status.HTTP_403_FORBIDDEN)

    logger.info('Login successful: %s', email)
    return Response(_token_response(user))


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def refresh(request):
    """POST /api/auth/refresh — exchange a refresh token for a fresh access token."""
    refresh_token = request.data.get('refresh_token') or request.data.get('refresh')
    if not refresh_token:
        return Response({'detail': 'refresh_token is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh_token)
        # Rotation + blacklist are enabled in settings, so this returns a new pair.
        access = token.access_token
        new_refresh = str(token)
        try:
            token.blacklist()
        except Exception:
            pass
    except (TokenError, InvalidToken) as exc:
        return Response({'detail': str(exc) or 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

    return Response({
        'access_token': str(access),
        'refresh_token': new_refresh,
        'token_type': 'bearer',
        'expires_in': int(access.lifetime.total_seconds()),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """POST /api/auth/logout — blacklist the refresh token."""
    refresh_token = request.data.get('refresh_token') or request.data.get('refresh')
    if refresh_token:
        try:
            RefreshToken(refresh_token).blacklist()
        except (TokenError, InvalidToken):
            pass
    return Response({'detail': 'Logged out'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """GET /api/auth/profile — current user's profile."""
    return Response(UserSerializer(request.user).data)
