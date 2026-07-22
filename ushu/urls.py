from django.conf import settings
from django.contrib import admin
from django.templatetags.static import static as static_url
from django.urls import include, re_path
from django.views.generic.base import RedirectView
from django.views.static import serve

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    # Browsers implicitly request /favicon.ico; redirect to the logo so it
    # stops 404ing on every page load.
    re_path(r'^favicon\.ico$', RedirectView.as_view(
        url=static_url('img/logo.png'), permanent=True)),
]

# Static files are served by WhiteNoise middleware (works with DEBUG=False).
# Media (country flags) is served here so it also survives DEBUG=False on the
# isolated venue LAN; disable with USHU_SERVE_MEDIA=0 behind a real web server.
if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve,
                {'document_root': settings.MEDIA_ROOT}),
    ]

urlpatterns += [
    re_path(r'^', include('tablo.urls')),
]
