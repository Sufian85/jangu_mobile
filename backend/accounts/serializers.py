from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address
from .validators import normalize_uganda_phone

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    # AbstractUser defines first_name/last_name with blank=True, which makes
    # ModelSerializer auto-generate them as required=False. Registration
    # needs both, so declare them explicitly to require non-blank values.
    first_name = serializers.CharField(required=True, allow_blank=False, max_length=150)
    last_name = serializers.CharField(required=True, allow_blank=False, max_length=150)
    # Declared explicitly (not left to ModelSerializer's auto-generation) so
    # the model field's auto-attached UniqueValidator - which compares the
    # raw input against normalized stored values and never matches - doesn't
    # shadow validate_phone() below with an inconsistent error message.
    phone = serializers.CharField()

    class Meta:
        model = User
        fields = ["phone", "password", "first_name", "last_name"]

    def validate_phone(self, value):
        # Normalize before the uniqueness check: the DB stores normalized
        # "+256..." phones, but the auto-generated UniqueValidator checks
        # the raw input against that queryset, so a duplicate submitted in
        # a different format (e.g. "0771234567" vs stored "+256771234567")
        # would slip past it and hit the DB as an unhandled IntegrityError.
        try:
            normalized = normalize_uganda_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        if User.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return normalized

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    # Same blank=True trap as RegisterSerializer above: without this, PATCH
    # can silently blank out a user's name (optional to omit on PATCH, but
    # rejected if explicitly sent empty).
    first_name = serializers.CharField(required=False, allow_blank=False, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=False, max_length=150)

    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "last_name"]
        read_only_fields = ["id", "phone"]


class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # ModelBackend.authenticate() looks phone up as a raw, unnormalized
        # value, but every stored phone is normalized to "+256..." on save.
        # Without this, a user registered with a local-format number
        # ("0771234567") could never log in with that same format. Silently
        # fall back to the raw value on a malformed phone so login always
        # returns a generic 401 rather than leaking a validation message.
        try:
            attrs[self.username_field] = normalize_uganda_phone(
                attrs[self.username_field]
            )
        except DjangoValidationError:
            pass
        return super().validate(attrs)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "recipient_name",
            "recipient_phone",
            "city_district",
            "street_area",
            "landmark",
            "is_default",
            "created_at",
        ]
        # is_default is deliberately read-only here (deviation from the
        # original plan snippet, per code review): if it were writable, a
        # client could PATCH {"is_default": false} on a user's only/current
        # default address and leave them with zero defaults, since
        # Address.save() only ever adds a default, never reassigns one when
        # the current default is turned off. All default-switching must go
        # through AddressViewSet.set_default instead.
        read_only_fields = ["id", "is_default", "created_at"]


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
