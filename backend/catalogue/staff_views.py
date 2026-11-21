from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .models import Category, Product, ProductImage, ProductVariant
from .staff_serializers import (
    StaffCategorySerializer,
    StaffProductImageSerializer,
    StaffProductSerializer,
    StaffProductVariantSerializer,
)


class StaffCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffCategorySerializer
    queryset = Category.objects.all()
    pagination_class = None


class StaffProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductSerializer
    queryset = Product.objects.all()
    pagination_class = None


class StaffProductVariantViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductVariantSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = ProductVariant.objects.all()
        product_id = self.request.query_params.get("product")
        if product_id is not None:
            if not product_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.request.query_params.get("product"))
        serializer.save(product=product)


class StaffProductImageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductImageSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = ProductImage.objects.all()
        product_id = self.request.query_params.get("product")
        if product_id is not None:
            if not product_id.isdigit():
                return queryset.none()
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.request.query_params.get("product"))
        serializer.save(product=product)

    @action(detail=True, methods=["post"], url_path="set-primary")
    def set_primary(self, request, pk=None):
        image = self.get_object()
        image.is_primary = True
        image.save()
        return Response(StaffProductImageSerializer(image).data)
