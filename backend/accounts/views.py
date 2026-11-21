from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Address, User
from .serializers import (
    AddressSerializer,
    LogoutSerializer,
    PhoneTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            # Belt-and-suspenders: validate_phone()'s existence check narrows
            # the duplicate-phone race but can't close it (two concurrent
            # requests can both pass the check before either commits). The
            # DB's unique constraint is the real guarantee; catch it here so
            # the unlucky racer gets a clean 400 instead of a 500.
            user = serializer.save()
        except IntegrityError:
            raise serializers.ValidationError(
                {"phone": ["A user with this phone number already exists."]}
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    # Not just TokenObtainPairView.as_view() directly: see
    # PhoneTokenObtainPairSerializer for why the stock serializer alone
    # can't authenticate a phone stored in normalized (+256...) form.
    serializer_class = PhoneTokenObtainPairSerializer
    throttle_scope = "login"


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError as exc:
            raise serializers.ValidationError({"refresh": [str(exc)]})
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    # PUT's full-replace semantics don't apply cleanly here (every writable
    # field is individually optional, so nothing actually gets "reset" on a
    # partial payload) - restrict to partial updates only.
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class AddressViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer
    # A user's addresses are a small, bounded-per-user collection (a few at
    # most), not something that should ever need paging - same reasoning as
    # CategoryListView. Without this, the project-wide DEFAULT_PAGINATION_CLASS
    # wraps the response in {"count", "next", "previous", "results"}, breaking
    # callers that expect a bare list.
    pagination_class = None

    def get_queryset(self):
        # drf-spectacular introspects this with an AnonymousUser (no real
        # request), which would crash the filter and leave the "id" path
        # param untyped in the generated schema. swagger_fake_view is the
        # standard flag it (and drf-yasg) sets during that pass.
        if getattr(self, "swagger_fake_view", False):
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        # Address.save() guarantees a default exists once a user has any
        # addresses, but that invariant only covers create/update - deleting
        # the current default would otherwise leave the user with zero
        # defaults. Promote the most recent remaining address in that case,
        # under the same user-row lock Address.save() uses.
        was_default = instance.is_default
        user_id = instance.user_id
        with transaction.atomic():
            User.objects.select_for_update().get(pk=user_id)
            instance.delete()
            if was_default:
                replacement = (
                    Address.objects.filter(user_id=user_id)
                    .order_by("-created_at")
                    .first()
                )
                if replacement is not None:
                    replacement.is_default = True
                    replacement.save()

    @extend_schema(request=None)
    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        address = self.get_object()
        address.is_default = True
        address.save()
        return Response(AddressSerializer(address).data)
