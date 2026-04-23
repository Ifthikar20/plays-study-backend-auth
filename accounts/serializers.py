"""Serializers for accounts app."""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """Registration request — validates email, name, password."""
    email = serializers.EmailField()
    name = serializers.CharField(max_length=255, min_length=1)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email already registered')
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Login request — email + password."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    """Public user profile data."""
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'xp', 'level', 'is_active', 'created_at']
        read_only_fields = fields
