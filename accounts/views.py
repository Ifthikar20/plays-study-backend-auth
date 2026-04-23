"""Auth views — Register, Login, Profile. All token responses match the existing FastAPI contract."""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthRateThrottle(AnonRateThrottle):
    rate = '10/minute'


def _token_response(user):
    """Generate JWT token pair and return response matching FastAPI contract."""
    refresh = RefreshToken.for_user(user)
    # Add email claim to match existing frontend expectations
    refresh['email'] = user.email
    refresh['sub'] = str(user.id)
    access = refresh.access_token
    access['email'] = user.email
    access['sub'] = str(user.id)

    return {
        'access_token': str(access),
        'token_type': 'bearer',
        'expires_in': int(access.lifetime.total_seconds()),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def register(request):
    """
    POST /api/auth/register
    Create a new user account and return JWT token.
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        # Return first error message as 'detail' to match FastAPI format
        first_error = next(iter(serializer.errors.values()))[0]
        return Response(
            {'detail': str(first_error)},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = serializer.save()
    logger.info(f'✅ New user registered: {user.email}')
    return Response(_token_response(user), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
def login(request):
    """
    POST /api/auth/login
    Authenticate and return JWT token.
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'detail': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    email = serializer.validated_data['email'].lower()
    password = serializer.validated_data['password']

    # Authenticate using Django's backend
    user = authenticate(request, username=email, password=password)

    if user is None:
        logger.warning(f'🔑 Login failed for: {email}')
        return Response(
            {'detail': 'Incorrect email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'detail': 'Account is inactive'},
            status=status.HTTP_403_FORBIDDEN
        )

    logger.info(f'🔑 Login successful: {email}')
    return Response(_token_response(user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    GET /api/auth/profile
    Return current user's profile.
    """
    return Response(UserSerializer(request.user).data)
