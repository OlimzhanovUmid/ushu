from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from . import forms
from .models import User


# Register your models here.
class UserAdmin(UserAdmin):
    list_display = ('username', 'category', 'is_staff', 'is_active')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'category',),
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
    )
    fieldsets = (
        (None, {'fields': ('username', 'password', 'category',)}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
            'description': _('To retire a judge who already has recorded '
                             'scores, uncheck "active" — deletion is blocked '
                             'to preserve competition history.'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_filter = ('category', 'is_staff', 'is_superuser', 'is_active', 'groups',)
    filter_horizontal = ('groups', 'user_permissions',)
    add_form = forms.UserCreationFormForAdmin


admin.site.register(User, UserAdmin)
