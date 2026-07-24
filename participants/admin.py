from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Participant

# Register your models here.


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_en', 'club', 'age_label', 'sex_label')
    list_filter = ('sex', 'age', 'club')
    search_fields = ('name_ru', 'name_en', 'club__name')
    list_select_related = ('club',)

    @admin.display(description=_('age'), ordering='age')
    def age_label(self, obj):
        return obj.get_age_display()

    @admin.display(description=_('sex'), ordering='sex')
    def sex_label(self, obj):
        return obj.get_sex_display()
