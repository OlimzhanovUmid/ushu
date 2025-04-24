from django.conf.urls import patterns, include, url, static
from django.contrib import admin
from django.conf import settings

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('tablo.urls')),
] + static.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static.static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

