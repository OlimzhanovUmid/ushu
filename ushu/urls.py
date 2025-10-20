from django.conf import settings
from django.conf.urls import include, url, static
from django.contrib import admin

urlpatterns = [
                  url(r'^admin/', admin.site.urls),
                  url(r'^', include('tablo.urls')),
              ] + static.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
              + static.static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
