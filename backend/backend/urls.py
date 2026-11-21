from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalogue.urls")),
    path("api/staff/catalogue/", include("catalogue.staff_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("", include("storefront.urls")),
]

# Serve uploaded media from the app process. Production nginx answers /media/
# itself (deploy/nginx-jangu.conf), so this only runs in local dev and tests.
# document_root is read per-request so test overrides of MEDIA_ROOT take effect.
def _serve_media(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", _serve_media),
]
