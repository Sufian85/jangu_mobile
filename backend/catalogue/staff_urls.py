from django.urls import include, path
from rest_framework import permissions
from rest_framework.routers import APIRootView, DefaultRouter

from .staff_views import (
    StaffCategoryViewSet,
    StaffProductImageViewSet,
    StaffProductVariantViewSet,
    StaffProductViewSet,
)


class StaffAPIRootView(APIRootView):
    permission_classes = [permissions.IsAdminUser]


router = DefaultRouter()
router.register("categories", StaffCategoryViewSet, basename="staff-category")
router.register("products", StaffProductViewSet, basename="staff-product")
router.register("variants", StaffProductVariantViewSet, basename="staff-variant")
router.register("images", StaffProductImageViewSet, basename="staff-image")
router.APIRootView = StaffAPIRootView

urlpatterns = [
    path("", include(router.urls)),
]
