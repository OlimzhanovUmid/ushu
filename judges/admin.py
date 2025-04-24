from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext, ugettext_lazy as _
from . import forms
from .models import User

# Register your models here.
class UserAdmin(UserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username','password1', 'password2', 'category',),
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
    )
    fieldsets = (
        (None, {'fields': ('username', 'password', 'category',)}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups',)
    filter_horizontal = ('groups', 'user_permissions',)
    add_form = forms.UserCreationFormForAdmin

admin.site.register(User, UserAdmin)

