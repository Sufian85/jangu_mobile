from django.db import models, transaction

from .utils import attribute_values, unique_slugify


class SlugManager(models.Manager):
    """Lets fixtures reference rows by slug instead of numeric id."""

    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class ProductVariantManager(models.Manager):
    def get_by_natural_key(self, sku):
        return self.get(sku=sku)


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    image = models.ImageField(upload_to="categories/", blank=True)

    objects = SlugManager()

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.slug,)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(Category, self.name, self.pk)
        super().save(*args, **kwargs)


class Product(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SlugManager()

    def __str__(self):
        return self.title

    def natural_key(self):
        return (self.slug,)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(Product, self.title, self.pk)
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)

    objects = ProductVariantManager()

    def __str__(self):
        return self.sku

    def natural_key(self):
        return (self.sku,)

    def save(self, *args, **kwargs):
        if not self.sku:
            value = " ".join([self.product.slug, *attribute_values(self.attributes)])
            self.sku = unique_slugify(ProductVariant, value, self.pk, field="sku", max_length=64)
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        return self.stock_qty > 0


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.title} image #{self.pk}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            Product.objects.select_for_update().get(pk=self.product_id)

            is_first_image = self._state.adding and not ProductImage.objects.filter(
                product=self.product
            ).exists()
            if is_first_image:
                self.is_primary = True

            super().save(*args, **kwargs)

            if self.is_primary:
                ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(
                    is_primary=False
                )
