import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def make_test_image(name="test.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")
