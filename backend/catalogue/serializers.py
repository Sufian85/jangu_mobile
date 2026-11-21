from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "image"]


class ProductListSerializer(serializers.ModelSerializer):
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "brand", "category", "primary_image",
            "price_from", "in_stock",
        ]

    def get_in_stock(self, obj) -> bool:
        return any(variant.stock_qty > 0 for variant in obj.variants.all())

    def get_primary_image(self, obj) -> str | None:
        primary = next((image for image in obj.images.all() if image.is_primary), None)
        if primary is None:
            return None
        request = self.context.get("request")
        url = primary.image.url
        return request.build_absolute_uri(url) if request else url


class ProductVariantSerializer(serializers.ModelSerializer):
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "attributes", "price", "stock_qty", "in_stock"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_primary", "sort_order"]


class ProductDetailSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "brand", "category", "description",
            "variants", "images",
        ]
