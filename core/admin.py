"""Admin-site branding for the Ushu Federation scoring app.

This module runs during admin autodiscovery (``AdminConfig.ready()``), before
any template is rendered, so it is the right place to (a) set the Russian
Federation site headers and (b) make the branded ``core/templates/admin/``
overrides win.

Template-override note: ``core`` is listed *after* ``django.contrib.admin`` in
``INSTALLED_APPS``, so the ``app_directories`` loader would find Django's own
``admin/base_site.html`` first. ``core/templates`` is registered in
``TEMPLATES['DIRS']`` (settings), which the filesystem loader checks *before*
app dirs, so the branded override wins — no custom AdminSite needed.
"""

from django.contrib import admin

# --- Russian Federation site headers --------------------------------------
admin.site.site_header = 'Судейская — администрирование'
admin.site.site_title = 'Ушу · Администрирование'
admin.site.index_title = 'Настройка и справочные данные'
