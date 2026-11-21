from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from accounts.models import Address
from accounts.validators import normalize_uganda_phone
from catalogue.models import ProductVariant

User = get_user_model()


class _VariantMixin(forms.Form):
    variant_id = forms.IntegerField(min_value=1)

    def clean_variant_id(self):
        vid = self.cleaned_data["variant_id"]
        variant = (
            ProductVariant.objects.filter(id=vid, product__is_active=True)
            .select_related("product")
            .first()
        )
        if variant is None:
            raise forms.ValidationError("That product is unavailable.")
        self.cleaned_data["variant"] = variant
        return vid


class AddToCartForm(_VariantMixin):
    quantity = forms.IntegerField(min_value=1, initial=1)


class UpdateCartForm(_VariantMixin):
    quantity = forms.IntegerField(min_value=0)


class PhoneAuthenticationForm(AuthenticationForm):
    """Login form: relabel the username field and normalise the phone so a
    number typed as ``0771…`` matches the stored ``+256771…`` value."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Phone"
        self.fields["username"].widget.attrs.update({"placeholder": "+2567…"})

    def clean(self):
        raw = self.cleaned_data.get("username")
        if raw:
            try:
                self.cleaned_data["username"] = normalize_uganda_phone(raw)
            except DjangoValidationError:
                pass
        return super().clean()


class RegisterForm(forms.Form):
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"placeholder": "+2567…"}))
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_phone(self):
        try:
            normalized = normalize_uganda_phone(self.cleaned_data["phone"])
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages)
        if User.objects.filter(phone=normalized).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return normalized

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        if p1:
            try:
                validate_password(p1)
            except DjangoValidationError as exc:
                self.add_error("password1", exc.messages)
        return cleaned

    def save(self):
        return User.objects.create_user(
            phone=self.cleaned_data["phone"],
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["recipient_name", "recipient_phone", "city_district", "street_area", "landmark"]

    def clean_recipient_phone(self):
        value = self.cleaned_data["recipient_phone"]
        try:
            return normalize_uganda_phone(value)
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages)
