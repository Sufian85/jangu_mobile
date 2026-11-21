from django.db import transaction
from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant


class StaffCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "image"]
        read_only_fields = ["slug"]


class StaffProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "attributes", "price", "stock_qty"]
        read_only_fields = ["id"]


class StaffProductSerializer(serializers.ModelSerializer):
    variants = StaffProductVariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "category", "description", "brand",
            "is_active", "variants",
        ]
        read_only_fields = ["slug"]

    def create(self, validated_data):
        variants_data = validated_data.pop("variants", [])
        if not variants_data:
            raise serializers.ValidationError(
                {"variants": "A product needs at least one variant."}
            )
        with transaction.atomic():
            product = Product.objects.create(**validated_data)
            for variant_data in variants_data:
                ProductVariant.objects.create(product=product, **variant_data)
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop("variants", None)
        if variants_data:
            raise serializers.ValidationError(
                {"variants": "Manage variants via the /variants/ endpoint, not by PATCHing the product."}
            )
        return super().update(instance, validated_data)


class StaffProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_primary", "sort_order"]
        # is_primary is deliberately read-only here, mirroring AddressSerializer's
        # is_default (see accounts/serializers.py): if it were writable, a client
        # could PATCH {"is_primary": false} on a product's only/current primary
        # image and leave it with zero primary images, since ProductImage.save()
        # only ever promotes a primary, never reassigns one when the current
        # primary is turned off. All primary-switching must go through
        # StaffProductImageViewSet.set_primary instead.
        read_only_fields = ["id", "is_primary"]
