from django.contrib.auth.models import AbstractUser
from django.db import models, transaction

from .managers import UserManager
from .validators import normalize_uganda_phone, validate_uganda_phone


class User(AbstractUser):
    username = None
    phone = models.CharField(
        max_length=13, unique=True, validators=[validate_uganda_phone]
    )
    email = models.EmailField(blank=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_uganda_phone(self.phone)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.phone


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=13, validators=[validate_uganda_phone])
    city_district = models.CharField(max_length=100)
    street_area = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.recipient_name} - {self.city_district}"

    def save(self, *args, **kwargs):
        if self.recipient_phone:
            self.recipient_phone = normalize_uganda_phone(self.recipient_phone)

        # Lock the parent user row so concurrent saves for the same user's
        # addresses (e.g. a double-tapped submit) are serialized. Without
        # this, two concurrent inserts can each see "no address yet", both
        # decide they're the first/default, and race each other's
        # unset-siblings update — leaving the user with zero defaults.
        with transaction.atomic():
            User.objects.select_for_update().get(pk=self.user_id)

            is_first_address = self._state.adding and not Address.objects.filter(
                user=self.user
            ).exists()
            if is_first_address:
                self.is_default = True

            super().save(*args, **kwargs)

            if self.is_default:
                Address.objects.filter(user=self.user).exclude(pk=self.pk).update(
                    is_default=False
                )
